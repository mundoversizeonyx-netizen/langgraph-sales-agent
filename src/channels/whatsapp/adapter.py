"""WhatsApp adapter para Evolution API - Vision Gemini para imagenes del cliente."""
from datetime import datetime, timezone
import httpx, os, base64

DRIVE_CATALOG = {
    "buso_dama": {
        "url": "https://drive.google.com/uc?export=view&id=1Y3mlU7uarKpz3VSbh2aqK4Ux2EKWh5V5",
        "descripcion": "Buso con chompa dama - algodon 100%, diseno anime"
    },
    "buso_hombre": {
        "url": "https://drive.google.com/uc?export=view&id=17o1dfQwWernIUvxrDNbGqhrYXPGH0vbg",
        "descripcion": "Buso con chompa hombre - algodon 100%, diseno anime"
    },
    "oversized": {
        "url": "https://drive.google.com/uc?export=view&id=1bXIyShTxpShjQOyewKFq4pLN_sosC6-4",
        "descripcion": "Camiseta oversized - diseno anime exclusivo"
    },
    "polo": {
        "url": "https://drive.google.com/uc?export=view&id=1qEObIVArr3-cv9Al6q-SLzYln-8dCmqW",
        "descripcion": "Camiseta tipo polo - diseno anime exclusivo"
    }
}

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
            or message.get("imageMessage", {}).get("caption", "")
            or ""
        )
        has_image = bool(message.get("imageMessage") or message.get("documentMessage"))
        phone = key.get("remoteJid", "").replace("@s.whatsapp.net", "").replace("@lid", "")
        tenant_id = os.getenv("DEFAULT_TENANT", "demo_store")
        final_text = f"[IMAGEN_CLIENTE]{text}" if has_image else text
        return InboundMessage(
            channel="whatsapp",
            channel_message_id=key.get("id", ""),
            channel_user_id=phone,
            tenant_id=tenant_id,
            thread_id=phone,
            text=final_text,
            received_at=datetime.now(timezone.utc),
            raw_payload=raw
        )

    async def _gemini_analyze(self, image_b64: str, mime: str, caption: str) -> str:
        """Analiza imagen del cliente con Gemini Vision. Detecta: comprobante, prenda/personaje anime, u otro."""
        keys = [
            os.getenv("GEMINI_API_KEY", ""),
            os.getenv("GEMINI_API_KEY_2", "")
        ]
        prompt = (
            "Eres un experto en anime y moda. Analiza esta imagen y responde en una sola linea con este formato exacto:\n"
            "TIPO: [comprobante | prenda | otro]\n"
            "DETALLE: [si es prenda describe el personaje o anime que ves; si es comprobante di 'pago'; si es otro di 'no relacionado']\n"
            f"Texto del cliente: '{caption}'\n"
            "Responde SOLO las dos lineas del formato. Nada mas."
        )
        body = {
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": image_b64}}
            ]}]
        }
        for key in keys:
            if not key:
                continue
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.post(url, json=body)
                    if r.status_code == 200:
                        text_out = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        print(f"[Gemini] Resultado: {text_out}")
                        return text_out
                    elif r.status_code == 429:
                        print(f"[Gemini] Key 1 rate limit, probando key 2...")
                        continue
            except Exception as e:
                print(f"[Gemini] Error: {e}")
                continue
        return "TIPO: otro\nDETALLE: no relacionado"

    async def _download_whatsapp_image(self, raw: dict) -> tuple:
        """Descarga imagen del mensaje de WhatsApp via Evolution API."""
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        data = raw.get("data", {})
        message = data.get("message", {})
        img_msg = message.get("imageMessage", {})
        if not img_msg:
            return None, "image/jpeg"
        mime = img_msg.get("mimetype", "image/jpeg")
        msg_key = data.get("key", {})
        msg_id = msg_key.get("id", "")
        remote_jid = msg_key.get("remoteJid", "")
        if not msg_id or not evo_url:
            return None, mime
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    f"{evo_url}/chat/getBase64FromMediaMessage/{instance}",
                    params={"id": msg_id, "convertToMp4": "false"},
                    headers={"apikey": evo_key}
                )
                if r.status_code == 200:
                    data_resp = r.json()
                    b64 = data_resp.get("base64", "") or data_resp.get("data", "")
                    if b64:
                        if "base64," in b64:
                            b64 = b64.split("base64,")[1]
                        return b64, mime
        except Exception as e:
            print(f"[Download] Error descargando imagen: {e}")
        return None, mime

    async def analyze_client_image(self, raw: dict) -> dict:
        """Analiza imagen del cliente. Retorna tipo y detalle."""
        data = raw.get("data", {})
        message = data.get("message", {})
        caption = message.get("imageMessage", {}).get("caption", "")
        caption_lower = caption.lower()
        payment_words = ["pague", "pago", "comprobante", "transferi", "ya pague", "hice el pago", "realice el pago"]
        if any(w in caption_lower for w in payment_words):
            return {"tipo": "comprobante", "detalle": "pago"}
        image_b64, mime = await self._download_whatsapp_image(raw)
        if image_b64:
            result = await self._gemini_analyze(image_b64, mime, caption)
            tipo = "otro"
            detalle = "no relacionado"
            for line in result.split("\n"):
                if line.startswith("TIPO:"):
                    tipo = line.replace("TIPO:", "").strip().lower()
                elif line.startswith("DETALLE:"):
                    detalle = line.replace("DETALLE:", "").strip()
            return {"tipo": tipo, "detalle": detalle}
        return {"tipo": "prenda", "detalle": caption or "imagen sin texto"}

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        owner = os.getenv("OWNER_NUMBER", "573043898187")
        if not evo_url:
            print("[WhatsApp] ERROR: EVOLUTION_URL no configurado")
            return
        headers = {"apikey": evo_key, "Content-Type": "application/json"}
        reply_text = message.text or ""
        url = f"{evo_url}/message/sendText/{instance}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={"number": channel_user_id, "text": reply_text}, headers=headers)
            if resp.status_code not in (200, 201):
                print(f"[WhatsApp] Error: {resp.status_code} {resp.text}")
            else:
                print(f"[WhatsApp] OK: {reply_text[:80]}")

    async def notify_owner(self, channel_user_id: str, motivo: str) -> None:
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        owner = os.getenv("OWNER_NUMBER", "573043898187")
        if not evo_url:
            return
        headers = {"apikey": evo_key, "Content-Type": "application/json"}
        url = f"{evo_url}/message/sendText/{instance}"
        msg = f"ONYX ALERTA - Cliente {channel_user_id} {motivo}. Revisa el chat."
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json={"number": owner, "text": msg}, headers=headers)
            print(f"[WhatsApp] Alerta dueno: {motivo}")