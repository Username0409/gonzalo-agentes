import httpx
import os
import logging

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
BASE_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}"


async def send_text_message(to: str, body: str) -> dict:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp credentials not configured — message not sent")
        return {"status": "skipped", "reason": "no_credentials"}

    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        data = resp.json()
        if resp.status_code == 200:
            logger.info(f"Message sent to {to}")
            return {"status": "sent", "wa_id": data.get("messages", [{}])[0].get("id")}
        else:
            logger.error(f"WhatsApp API error: {data}")
            return {"status": "error", "detail": data}


async def send_template_message(to: str, template_name: str, language: str = "es") -> dict:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"status": "skipped", "reason": "no_credentials"}

    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {"name": template_name, "language": {"code": language}},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        return resp.json()


async def send_interactive_buttons(to: str, body: str, buttons: list[dict]) -> dict:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"status": "skipped", "reason": "no_credentials"}

    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    btn_list = []
    for i, b in enumerate(buttons[:3]):
        btn_list.append({
            "type": "reply",
            "reply": {"id": f"btn_{i}", "title": b["title"][:20]},
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": btn_list},
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        return resp.json()


def extract_message_data(webhook_body: dict) -> list[dict]:
    messages = []
    for entry in webhook_body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" not in value:
                continue
            contact_info = value.get("contacts", [{}])[0]
            for msg in value["messages"]:
                extracted = {
                    "from": msg.get("from", ""),
                    "wa_id": msg.get("id", ""),
                    "timestamp": msg.get("timestamp", ""),
                    "type": msg.get("type", "text"),
                    "contact_name": contact_info.get("profile", {}).get("name", ""),
                }
                if msg["type"] == "text":
                    extracted["body"] = msg.get("text", {}).get("body", "")
                elif msg["type"] == "interactive":
                    reply = msg.get("interactive", {}).get("button_reply", {})
                    extracted["body"] = reply.get("title", "")
                    extracted["button_id"] = reply.get("id", "")
                elif msg["type"] == "image":
                    extracted["body"] = "[Imagen recibida]"
                    extracted["media_id"] = msg.get("image", {}).get("id", "")
                elif msg["type"] == "audio":
                    extracted["body"] = "[Audio recibido]"
                    extracted["media_id"] = msg.get("audio", {}).get("id", "")
                else:
                    extracted["body"] = f"[{msg['type']}]"
                messages.append(extracted)
    return messages
