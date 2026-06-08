"""WhatsApp adapter para Evolution API - con vision Gemini para imagenes."""
from datetime import datetime, timezone
import httpx, os, base64, json

EVO_URL = ""
EVO_KEY = ""
INSTANCE = ""
OWNER = ""
GEMINI_KEY = ""

def _init_env():
    global EVO_URL, EVO_KEY, INSTANCE, OWNER, GEMINI_KEY
    EVO_URL = os.getenv("EVOLUTION_URL", "")
    EVO_KEY = os.getenv("EVOLUTION_API_KEY", "")
    INSTANCE = os.getenv("EVOLUTION_INSTANCE", "demo")
    OWNER = os.getenv("OWNER_NUMBER", "573043898187")
    GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage

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
        has_image = bool(
            message.get("imageMessage")
            or message.get("documentMessage")
        )
        phone = key.get("remoteJid", "").replace("@s.whatsapp.net", "").replace("@lid", "")
        tenant_id = os.getenv("DEFAULT_TENANT", "demo_store")
        return InboundMessage(
            channel="whatsapp",
            channel_message_id=key.get("id", ""),
            channel_user_id=phone,
            tenant_id=tenant_id,
            thread_id=phone,
            text=text if not has_image else f"[IMAGEN]{text}",
            received_at=datetime.now(timezone.utc),
            raw_payload=raw
        )

    async def _analyze_image_gemini(self, image_b64: str, mime: str, caption: str) -> str:
        """Usa Gemini Flash para analizar si es comprobante de pago o foto de prenda."""
        _init_env()
        if not GEMINI_KEY:
            return "imagen"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
        prompt = (
            "Analiza esta imagen. Responde UNICAMENTE con una de estas palabras: "
            "'comprobante' si es un recibo, transferencia o pago bancario, "
            "'prenda' si es ropa o producto de moda, "
            "'otro' si es cualquier otra cosa. "
            f"Texto adicional del cliente: '{caption}'"
        )
        body = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": image_b64}}
                ]
            }]
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=body)
            if r.status_code == 200:
                result = r.json()
                text_out = result["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
                if "comprobante" in text_out:
                    return "comprobante"
                elif "prenda" in text_out:
                    return "prenda"
        return "otro"

    async def _download_image(self, message: dict, client: httpx.AsyncClient) -> tuple:
        """Descarga imagen desde Evolution API."""
        _init_env()
        img_msg = message.get("imageMessage", {})
        if not img_msg:
            return None, None
        mime = img_msg.get("mimetype", "image/jpeg")
        return None, mime

    async def handle_image_message(self, raw: dict) -> str:
        """Procesa mensaje con imagen y retorna tipo: comprobante/prenda/otro."""
        data = raw.get("data", {})
        message = data.get("message", {})
        img_msg = message.get("imageMessage", {})
        caption = img_msg.get("caption", "")
        caption_lower = caption.lower()
        payment_words = ["pague", "pago", "transferi", "comprobante", "ya pague", "listo pague", "hice el pago"]
        if any(w in caption_lower for w in payment_words):
            return "comprobante"
        return "prenda"

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        _init_env()
        if not EVO_URL:
            print("[WhatsApp] ERROR: EVOLUTION_URL no configurado")
            return
        headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
        reply_text = message.text or ""
        url = f"{EVO_URL}/message/sendText/{INSTANCE}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={"number": channel_user_id, "text": reply_text}, headers=headers)
            if resp.status_code not in (200, 201):
                print(f"[WhatsApp] Error: {resp.status_code} {resp.text}")
            else:
                print(f"[WhatsApp] OK: {reply_text[:80]}")

    async def notify_owner(self, channel_user_id: str, motivo: str) -> None:
        _init_env()
        if not EVO_URL:
            return
        headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
        url = f"{EVO_URL}/message/sendText/{INSTANCE}"
        msg = f"ONYX ALERTA - Cliente {channel_user_id} {motivo}. Revisa el chat."
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json={"number": OWNER, "text": msg}, headers=headers)
            print(f"[WhatsApp] Alerta enviada al dueno: {motivo}")