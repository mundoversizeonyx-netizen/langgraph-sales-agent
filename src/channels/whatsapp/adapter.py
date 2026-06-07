"""WhatsApp adapter para Evolution API (Baileys) - NO Meta Cloud API."""
from datetime import datetime, timezone
import httpx
import os
from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage

PAYMENT_KEYWORDS = ["comprobante", "pague", "pago", "transferi", "ya pague", "ya pago", "realice el pago", "hice el pago", "envio el comprobante"]

class WhatsAppAdapter(ChannelAdapter):
    def parse_webhook(self, raw: dict) -> InboundMessage:
        data = raw.get("data", {})
        key = data.get("key", {})
        message = data.get("message", {})
        text = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or ""
        )
        phone = key.get("remoteJid", "").replace("@s.whatsapp.net", "").replace("@lid", "")
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
        evolution_url = os.getenv("EVOLUTION_URL", "")
        evolution_api_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "default")
        owner_number = os.getenv("OWNER_NUMBER", "573043898187")
        if not evolution_url:
            print("[WhatsApp] ERROR: EVOLUTION_URL no configurado")
            return
        headers = {"apikey": evolution_api_key, "Content-Type": "application/json"}
        reply_text = message.text or ""
        async with httpx.AsyncClient(timeout=30) as client:
            # Enviar respuesta al cliente
            url = f"{evolution_url}/message/sendText/{instance}"
            payload = {"number": channel_user_id, "text": reply_text}
            print(f"[WhatsApp] Enviando a {url} - numero: {channel_user_id}")
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                print(f"[WhatsApp] Error: {resp.status_code} {resp.text}")
            else:
                print(f"[WhatsApp] OK: {reply_text[:80]}")
            # Notificar al dueno si el cliente menciona pago
            msg_lower = reply_text.lower()
            if any(kw in msg_lower for kw in ["comprobante", "pedido queda agendado", "pago recibido", "pago confirmado"]):
                notif = f"ONYX ALERTA - Cliente {channel_user_id} confirmo pago. Revisa el chat."
                await client.post(url, json={"number": owner_number, "text": notif}, headers=headers)
                print(f"[WhatsApp] Notificacion enviada al dueno")