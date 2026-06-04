import os
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


async def generate_response(
    user_message: str,
    contact_name: str,
    business_name: str,
    products: list[dict],
    conversation_history: list[dict],
    tone: str = "amigable",
) -> str:
    if not ANTHROPIC_API_KEY:
        return _fallback_response(user_message, business_name)

    product_catalog = ""
    if products:
        lines = []
        for p in products[:20]:
            lines.append(f"- {p['name']}: S/{p['price']:.2f} — {p['description']}")
        product_catalog = "\n".join(lines)

    history_text = ""
    if conversation_history:
        for msg in conversation_history[-10:]:
            role = "Cliente" if msg["direction"] == "in" else "Agente"
            history_text += f"{role}: {msg['message']}\n"

    system_prompt = f"""Eres el asistente virtual de "{business_name}", un negocio en Lima, Peru.

REGLAS:
- Responde siempre en español peruano, de forma {tone} y profesional.
- Maximo 300 caracteres por respuesta para WhatsApp.
- Si el cliente pregunta por un producto, usa el catalogo real.
- Si no puedes resolver algo, ofrece conectar con un asesor humano.
- Nunca inventes precios ni productos que no estan en el catalogo.
- Usa emojis con moderacion (1-2 por mensaje).
- Si el cliente saluda, responde con bienvenida y menu de opciones.
- Cierra siempre con una pregunta o invitacion a seguir la conversacion.

CATALOGO DE PRODUCTOS:
{product_catalog if product_catalog else "No hay productos cargados aun."}

HISTORIAL RECIENTE:
{history_text if history_text else "Primera interaccion con este cliente."}
"""

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return _fallback_response(user_message, business_name)


def _fallback_response(message: str, business_name: str) -> str:
    msg = message.lower().strip()
    if any(w in msg for w in ["hola", "buenos", "buenas", "hi"]):
        return f"Hola! Bienvenido a {business_name} 👋\n\n1. Ver productos\n2. Precios\n3. Horario\n4. Hablar con asesor"
    if any(w in msg for w in ["precio", "costo", "cuanto"]):
        return "Te envio nuestro catalogo con precios actualizados. Que producto te interesa? 📋"
    if any(w in msg for w in ["horario", "hora", "abierto"]):
        return "Nuestro horario es de Lunes a Sabado, 9am a 7pm. Te esperamos! 🕐"
    if any(w in msg for w in ["gracias", "thank"]):
        return "Gracias a ti! Si necesitas algo mas, aqui estamos 24/7 😊"
    if any(w in msg for w in ["asesor", "persona", "humano"]):
        return "Te conecto con un asesor ahora mismo. Un momento por favor 🙋"
    return f"Gracias por escribirnos a {business_name}! En que podemos ayudarte? 😊"


async def generate_post_text(
    product_name: str, product_description: str, platform: str = "instagram"
) -> dict:
    if not ANTHROPIC_API_KEY:
        return {
            "text": f"Nuevo en stock: {product_name}! {product_description}. Consulta precios por DM 📩",
            "hashtags": "#gamarra #lima #moda #ofertas #peru",
        }

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"""Genera un texto corto para {platform} para el producto:
Nombre: {product_name}
Descripcion: {product_description}

Responde SOLO con formato JSON:
{{"text": "texto del post", "hashtags": "#hashtag1 #hashtag2 ..."}}""",
                }
            ],
        )
        import json
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"text": text, "hashtags": "#gamarra #lima #moda"}
    except Exception as e:
        logger.error(f"Post generation error: {e}")
        return {
            "text": f"Nuevo: {product_name}! {product_description}",
            "hashtags": "#gamarra #lima #ofertas",
        }
