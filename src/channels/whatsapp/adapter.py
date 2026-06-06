"""WhatsApp adapter para Evolution API (Baileys) — NO Meta Cloud API."""
from datetime import datetime, timezone
import httpx
import os
from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage

EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")

class WhatsAppAdapter(ChannelAdapter):
    def parse_webhook(self, raw: dict) -> InboundMessage:
        """Parsea webhook de Evolution API."""
        data = raw.get("data", {})
        key = data.get("key", {})
        message = data.get("message", {})
        text = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or ""
        )
        phone = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
        instance = raw.get("instance", "default")
        tenant_id = os.getenv("DEFAULT_TENANT", "demo_store")
        return InboundMessage(
            channel="whatsapp",
            channel_message_id=key.get("id", ""),
            channel_user_id=phone,
            tenant_id=tenant_id,
            thread_id=phone,
            text=text,
            received_at=datetime.now(timezone.utc),
            raw_payload=raw
        )

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        """Envia respuesta via Evolution API."""
        instance = os.getenv("EVOLUTION_INSTANCE", "default")
        url = f"{EVOLUTION_URL}/message/sendText/{instance}"
        headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
        payload = {
            "number": channel_user_id,
            "text": message.text or ""
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                print(f"[WhatsApp] Error enviando: {resp.status_code} {resp.text}")
            else:
                print(f"[WhatsApp] Enviado a {channel_user_id}: {message.text[:50]}")
