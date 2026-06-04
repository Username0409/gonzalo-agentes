import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from database import DB_PATH
from auth import authenticate_user, create_access_token, get_current_user
from models.schemas import (
    LoginRequest, MessageSend, ContactCreate, ProductCreate, ProductUpdate,
    CampaignCreate, BotConfigUpdate, AutoResponseCreate,
)
from services.whatsapp import send_text_message
from services.ai_agent import generate_post_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["API"])


# ──────────── AUTH ────────────

@router.post("/login")
async def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "user": user}


# ──────────── DASHBOARD ────────────

@router.get("/dashboard")
async def get_dashboard(user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        today = datetime.utcnow().strftime("%Y-%m-%d")
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

        total_contacts = (await (await db.execute("SELECT COUNT(*) c FROM contacts")).fetchone())["c"]
        today_messages = (await (await db.execute(
            "SELECT COUNT(*) c FROM conversations WHERE created_at >= ?", (today,)
        )).fetchone())["c"]
        today_leads = (await (await db.execute(
            "SELECT COUNT(*) c FROM contacts WHERE created_at >= ?", (today,)
        )).fetchone())["c"]
        total_products = (await (await db.execute(
            "SELECT COUNT(*) c FROM products WHERE is_active = 1"
        )).fetchone())["c"]

        chart_rows = await db.execute("""
            SELECT date(created_at) as dia,
                   SUM(CASE WHEN direction='in' THEN 1 ELSE 0 END) as entrantes,
                   SUM(CASE WHEN direction='out' THEN 1 ELSE 0 END) as salientes
            FROM conversations
            WHERE created_at >= ?
            GROUP BY date(created_at) ORDER BY dia
        """, (week_ago,))
        chart_data = [dict(r) for r in await chart_rows.fetchall()]

        recent_rows = await db.execute("""
            SELECT c.phone, c.name, cv.message, cv.direction, cv.created_at
            FROM conversations cv
            JOIN contacts c ON c.id = cv.contact_id
            ORDER BY cv.created_at DESC LIMIT 10
        """)
        recent_messages = [dict(r) for r in await recent_rows.fetchall()]

        segment_rows = await db.execute(
            "SELECT segment, COUNT(*) c FROM contacts GROUP BY segment"
        )
        segments = {r["segment"]: r["c"] for r in await segment_rows.fetchall()}

    return {
        "total_contacts": total_contacts,
        "today_messages": today_messages,
        "today_leads": today_leads,
        "total_products": total_products,
        "chart_data": chart_data,
        "recent_messages": recent_messages,
        "segments": segments,
    }


# ──────────── CONTACTS ────────────

@router.get("/contacts")
async def list_contacts(user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT * FROM contacts ORDER BY last_message_at DESC")
        return [dict(r) for r in await rows.fetchall()]


@router.post("/contacts")
async def create_contact(contact: ContactCreate, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO contacts (phone, name, email, segment, tags) VALUES (?, ?, ?, ?, ?)",
                (contact.phone, contact.name, contact.email, contact.segment, contact.tags),
            )
            await db.commit()
            return {"status": "created"}
        except aiosqlite.IntegrityError:
            raise HTTPException(status_code=400, detail="El contacto ya existe")


# ──────────── CONVERSATIONS ────────────

@router.get("/conversations/{contact_id}")
async def get_conversations(contact_id: int, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute(
            "SELECT * FROM conversations WHERE contact_id = ? ORDER BY created_at ASC",
            (contact_id,),
        )
        return [dict(r) for r in await rows.fetchall()]


@router.post("/send-message")
async def send_message(msg: MessageSend, user=Depends(get_current_user)):
    result = await send_text_message(msg.phone, msg.message)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute("SELECT id FROM contacts WHERE phone = ?", (msg.phone,))
        contact = await row.fetchone()
        if contact:
            await db.execute(
                "INSERT INTO conversations (contact_id, direction, message, wa_message_id) VALUES (?, 'out', ?, ?)",
                (contact["id"], msg.message, result.get("wa_id", "")),
            )
            await db.commit()

    return result


# ──────────── PRODUCTS ────────────

@router.get("/products")
async def list_products(user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT * FROM products ORDER BY created_at DESC")
        return [dict(r) for r in await rows.fetchall()]


@router.post("/products")
async def create_product(product: ProductCreate, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO products (name, description, price, category, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)",
            (product.name, product.description, product.price, product.category, product.image_url, product.stock),
        )
        await db.commit()
        return {"status": "created"}


@router.put("/products/{product_id}")
async def update_product(product_id: int, product: ProductUpdate, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        fields = {k: v for k, v in product.model_dump().items() if v is not None}
        if not fields:
            return {"status": "no_changes"}
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [product_id]
        await db.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
        await db.commit()
        return {"status": "updated"}


@router.delete("/products/{product_id}")
async def delete_product(product_id: int, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()
        return {"status": "deleted"}


# ──────────── CAMPAIGNS ────────────

@router.get("/campaigns")
async def list_campaigns(user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
        return [dict(r) for r in await rows.fetchall()]


@router.post("/campaigns")
async def create_campaign(campaign: CampaignCreate, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO campaigns (name, message_template, segment_filter, scheduled_at) VALUES (?, ?, ?, ?)",
            (campaign.name, campaign.message_template, campaign.segment_filter, campaign.scheduled_at),
        )
        await db.commit()
        return {"status": "created"}


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: int, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        campaign = await (await db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))).fetchone()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaña no encontrada")

        segment = campaign["segment_filter"]
        if segment and segment != "todos":
            contacts = await (await db.execute(
                "SELECT phone FROM contacts WHERE segment = ?", (segment,)
            )).fetchall()
        else:
            contacts = await (await db.execute("SELECT phone FROM contacts")).fetchall()

        sent = 0
        for c in contacts:
            result = await send_text_message(c["phone"], campaign["message_template"])
            if result.get("status") == "sent":
                sent += 1

        await db.execute(
            "UPDATE campaigns SET status = 'sent', sent_count = ? WHERE id = ?",
            (sent, campaign_id),
        )
        await db.commit()

    return {"status": "sent", "sent_count": sent, "total_contacts": len(contacts)}


# ──────────── BOT CONFIG ────────────

@router.get("/config")
async def get_config(user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT key, value FROM bot_config")
        return {r["key"]: r["value"] for r in await rows.fetchall()}


@router.put("/config")
async def update_config(cfg: BotConfigUpdate, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bot_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (cfg.key, cfg.value, cfg.value),
        )
        await db.commit()
        return {"status": "updated"}


# ──────────── AUTO RESPONSES ────────────

@router.get("/auto-responses")
async def list_auto_responses(user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT * FROM auto_responses ORDER BY priority DESC")
        return [dict(r) for r in await rows.fetchall()]


@router.post("/auto-responses")
async def create_auto_response(ar: AutoResponseCreate, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO auto_responses (trigger_keyword, response_text, is_active, priority) VALUES (?, ?, ?, ?)",
            (ar.trigger_keyword, ar.response_text, ar.is_active, ar.priority),
        )
        await db.commit()
        return {"status": "created"}


@router.delete("/auto-responses/{response_id}")
async def delete_auto_response(response_id: int, user=Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM auto_responses WHERE id = ?", (response_id,))
        await db.commit()
        return {"status": "deleted"}


# ──────────── AI POST GENERATOR ────────────

@router.post("/generate-post")
async def generate_post(
    product_name: str, product_description: str = "", platform: str = "instagram",
    user=Depends(get_current_user),
):
    result = await generate_post_text(product_name, product_description, platform)
    return result


# ──────────── WSP CONNECTION STATUS ────────────

@router.get("/whatsapp-status")
async def whatsapp_status(user=Depends(get_current_user)):
    import os
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    return {
        "connected": bool(token and phone_id),
        "phone_id": phone_id[-4:] if phone_id else "",
        "has_token": bool(token),
    }
