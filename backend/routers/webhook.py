import os
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Response, Query
import aiosqlite
from services.whatsapp import extract_message_data, send_text_message
from services.ai_agent import generate_response
from database import DB_PATH

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "gonzalo_agentes_2026")


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("Webhook verification failed")
    return Response(content="Forbidden", status_code=403)


@router.post("")
async def receive_webhook(request: Request):
    body = await request.json()
    messages = extract_message_data(body)

    for msg in messages:
        await _process_incoming_message(msg)

    return {"status": "ok"}


async def _process_incoming_message(msg: dict):
    phone = msg["from"]
    text = msg.get("body", "")
    contact_name = msg.get("contact_name", "")
    wa_id = msg.get("wa_id", "")

    if not text:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        row = await db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,))
        contact = await row.fetchone()

        if contact is None:
            await db.execute(
                "INSERT INTO contacts (phone, name, segment) VALUES (?, ?, 'nuevo')",
                (phone, contact_name),
            )
            await db.commit()
            row = await db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,))
            contact = await row.fetchone()

        contact_id = contact["id"]

        await db.execute(
            """INSERT INTO conversations (contact_id, direction, message, message_type, wa_message_id)
               VALUES (?, 'in', ?, 'text', ?)""",
            (contact_id, text, wa_id),
        )
        await db.execute(
            "UPDATE contacts SET total_messages = total_messages + 1, last_message_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), contact_id),
        )
        await db.commit()

        await db.execute(
            """INSERT INTO metrics (metric_type, value, label) VALUES ('message_in', 1, ?)""",
            (phone,),
        )
        await db.commit()

        agent_active = await _get_config(db, "agent_active")
        if agent_active != "true":
            return

        ai_enabled = await _get_config(db, "ai_enabled")
        business_name = await _get_config(db, "business_name")
        tone = await _get_config(db, "tone")

        auto_reply = await _check_auto_responses(db, text, business_name)

        if auto_reply:
            reply = auto_reply
        elif ai_enabled == "true":
            history_rows = await db.execute(
                "SELECT direction, message FROM conversations WHERE contact_id = ? ORDER BY created_at DESC LIMIT 10",
                (contact_id,),
            )
            history = [dict(r) for r in await history_rows.fetchall()]
            history.reverse()

            product_rows = await db.execute(
                "SELECT name, price, description FROM products WHERE is_active = 1"
            )
            products = [dict(r) for r in await product_rows.fetchall()]

            reply = await generate_response(
                user_message=text,
                contact_name=contact_name or contact["name"],
                business_name=business_name,
                products=products,
                conversation_history=history,
                tone=tone,
            )
        else:
            reply = await _get_config(db, "welcome_message")
            reply = reply.replace("{business_name}", business_name)

        result = await send_text_message(phone, reply)

        await db.execute(
            """INSERT INTO conversations (contact_id, direction, message, message_type, wa_message_id)
               VALUES (?, 'out', ?, 'text', ?)""",
            (contact_id, reply, result.get("wa_id", "")),
        )
        await db.execute(
            """INSERT INTO metrics (metric_type, value, label) VALUES ('message_out', 1, ?)""",
            (phone,),
        )
        await db.commit()

    logger.info(f"Processed message from {phone}: '{text[:50]}...'")


async def _get_config(db, key: str) -> str:
    row = await db.execute("SELECT value FROM bot_config WHERE key = ?", (key,))
    result = await row.fetchone()
    return result["value"] if result else ""


async def _check_auto_responses(db, message: str, business_name: str) -> str | None:
    msg_lower = message.lower().strip()
    rows = await db.execute(
        "SELECT trigger_keyword, response_text FROM auto_responses WHERE is_active = 1 ORDER BY priority DESC"
    )
    for row in await rows.fetchall():
        if row["trigger_keyword"].lower() in msg_lower:
            response = row["response_text"]
            response = response.replace("{business_name}", business_name)
            config_keys = ["business_hours", "business_address"]
            for k in config_keys:
                val = await _get_config(db, k)
                response = response.replace(f"{{{k}}}", val)
            return response
    return None
