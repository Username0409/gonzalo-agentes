from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ContactCreate(BaseModel):
    phone: str
    name: str = ""
    email: str = ""
    segment: str = "nuevo"
    tags: str = ""


class ContactOut(BaseModel):
    id: int
    phone: str
    name: str
    email: str
    segment: str
    tags: str
    total_messages: int
    last_message_at: Optional[str]
    created_at: str


class MessageSend(BaseModel):
    phone: str
    message: str


class CampaignCreate(BaseModel):
    name: str
    message_template: str
    segment_filter: str = "todos"
    scheduled_at: Optional[str] = None


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float = 0
    category: str = ""
    image_url: str = ""
    stock: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    stock: Optional[int] = None


class BotConfigUpdate(BaseModel):
    key: str
    value: str


class AutoResponseCreate(BaseModel):
    trigger_keyword: str
    response_text: str
    is_active: bool = True
    priority: int = 0


class LoginRequest(BaseModel):
    username: str
    password: str


class WhatsAppWebhookEntry(BaseModel):
    object: str
    entry: list
