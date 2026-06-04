import aiosqlite
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "agente_marketing.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                segment TEXT DEFAULT 'nuevo',
                tags TEXT DEFAULT '',
                total_messages INTEGER DEFAULT 0,
                last_message_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                direction TEXT NOT NULL, -- 'in' or 'out'
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'text', -- text, image, audio, document
                wa_message_id TEXT,
                status TEXT DEFAULT 'sent', -- sent, delivered, read
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message_template TEXT NOT NULL,
                segment_filter TEXT DEFAULT 'todos',
                status TEXT DEFAULT 'draft', -- draft, scheduled, sent
                scheduled_at TEXT,
                sent_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                price REAL DEFAULT 0,
                category TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                stock INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                label TEXT DEFAULT '',
                recorded_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bot_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auto_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_keyword TEXT NOT NULL,
                response_text TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 0
            );
        """)

        existing = await db.execute("SELECT COUNT(*) FROM bot_config")
        count = (await existing.fetchone())[0]
        if count == 0:
            defaults = [
                ("business_name", "Mi Negocio"),
                ("welcome_message", "Hola! Bienvenido a {business_name}. Soy tu asistente virtual y estoy aqui para ayudarte 24/7.\n\nElige una opcion:\n1. Ver productos\n2. Precios\n3. Horario\n4. Hablar con un asesor"),
                ("tone", "amigable"),
                ("business_hours", "Lunes a Sabado 9am - 7pm"),
                ("business_address", "Lima, Peru"),
                ("agent_active", "true"),
                ("ai_enabled", "true"),
            ]
            await db.executemany(
                "INSERT INTO bot_config (key, value) VALUES (?, ?)", defaults
            )

        existing_resp = await db.execute("SELECT COUNT(*) FROM auto_responses")
        resp_count = (await existing_resp.fetchone())[0]
        if resp_count == 0:
            responses = [
                ("hola", "Hola! Bienvenido a {business_name}. Como puedo ayudarte hoy?", 1, 10),
                ("precio", "Nuestros precios varian segun el producto. Te envio nuestro catalogo actualizado:", 1, 8),
                ("horario", "Nuestro horario de atencion es: {business_hours}. Te esperamos!", 1, 8),
                ("ubicacion", "Estamos ubicados en: {business_address}. Te esperamos!", 1, 8),
                ("gracias", "Gracias a ti por comunicarte! Si necesitas algo mas, aqui estamos.", 1, 5),
                ("catalogo", "Te comparto nuestro catalogo de productos. Cual te interesa?", 1, 7),
                ("delivery", "Si, hacemos delivery! El costo varia segun tu ubicacion. Donde te encuentras?", 1, 7),
                ("asesor", "Te conecto con un asesor ahora mismo. Un momento por favor.", 1, 9),
            ]
            await db.executemany(
                "INSERT INTO auto_responses (trigger_keyword, response_text, is_active, priority) VALUES (?, ?, ?, ?)",
                responses,
            )

        await db.commit()
