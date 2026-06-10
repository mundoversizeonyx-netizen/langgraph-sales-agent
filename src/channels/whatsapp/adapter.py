"""WhatsApp adapter - Vision Gemini. Descarga imagen via POST (metodo correcto Evolution API)."""
from datetime import datetime, timezone
import httpx, os, re

from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage

NEQUI_NUMBER = "3132721394"
PRECIOS = {"oversized": 90000, "polo": 90000, "buso": 130000}

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

    async def _download_image(self, raw: dict) -> tuple:
        """Descarga imagen usando POST con body - metodo correcto segun docs Evolution API."""
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        data = raw.get("data", {})
        message = data.get("message", {})
        img_msg = message.get("imageMessage", {})
        if not img_msg or not evo_url:
            return None, "image/jpeg"
        mime = img_msg.get("mimetype", "image/jpeg")
        msg_id = data.get("key", {}).get("id", "")
        if not msg_id:
            return None, mime
        try:
            body = {"message": {"key": {"id": msg_id}}, "convertToMp4": False}
            async with httpx.AsyncClient(timeout=25) as client:
                r = await client.post(
                    f"{evo_url}/chat/getBase64FromMediaMessage/{instance}",
                    json=body,
                    headers={"apikey": evo_key, "Content-Type": "application/json"}
                )
                print(f"[Download] Status: {r.status_code} | msg_id: {msg_id}")
                if r.status_code in (200, 201):
                    resp = r.json()
                    b64 = resp.get("base64", "") or resp.get("data", "")
                    if b64:
                        if "base64," in b64:
                            b64 = b64.split("base64,")[1]
                        print(f"[Download] Imagen descargada OK, mime: {mime}, bytes_b64: {len(b64)}")
                        return b64, mime
                    else:
                        print(f"[Download] Respuesta sin base64: {resp}")
                else:
                    print(f"[Download] Error {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[Download] Excepcion: {e}")
        return None, mime

    async def _gemini_analyze(self, image_b64: str, mime: str, caption: str) -> dict:
        keys = [os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_API_KEY_2", "")]
        prompt = (
            "Analiza esta imagen con maxima precision.\n\n"
            "CASO 1 - COMPROBANTE DE PAGO: Si ves transferencia exitosa, recibo bancario, pantalla Nequi/Bancolombia/pago, comprobante:\n"
            "TIPO: comprobante\n"
            f"NEQUI_OK: si (solo si ves el numero {NEQUI_NUMBER} en la imagen) o no\n"
            "MONTO: [valor exacto en numeros que aparece en la imagen, ej: 90000]\n"
            "ANIME: ninguno\n"
            "PRENDA: ninguna\n\n"
            "CASO 2 - PRENDA DE ROPA: Si ves una camiseta, buso, polo con estampado:\n"
            "TIPO: prenda\n"
            "NEQUI_OK: no\n"
            "MONTO: ninguno\n"
            "ANIME: [nombre exacto del personaje y serie del estampado, o 'no identificado']\n"
            "PRENDA: [oversized | polo | buso]\n\n"
            "CASO 3 - OTRA COSA:\n"
            "TIPO: otro\nNEQUI_OK: no\nMONTO: ninguno\nANIME: ninguno\nPRENDA: ninguna\n\n"
            f"Caption del cliente: '{caption}'\n"
            "Responde UNICAMENTE las 5 lineas. Sin explicacion adicional."
        )
        body = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": image_b64}}]}]}
        for k in keys:
            if not k:
                continue
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={k}"
                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(url, json=body)
                    if r.status_code in (200, 201):
                        out = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        print(f"[Gemini] Resultado: {out}")
                        parsed = {"tipo": "otro", "nequi_ok": False, "monto": "", "anime": "no identificado", "prenda": "prenda"}
                        for line in out.split("\n"):
                            line = line.strip()
                            if line.startswith("TIPO:"):
                                parsed["tipo"] = line.replace("TIPO:", "").strip().lower()
                            elif line.startswith("NEQUI_OK:"):
                                parsed["nequi_ok"] = "si" in line.replace("NEQUI_OK:", "").strip().lower()
                            elif line.startswith("MONTO:"):
                                parsed["monto"] = line.replace("MONTO:", "").strip()
                            elif line.startswith("ANIME:"):
                                parsed["anime"] = line.replace("ANIME:", "").strip()
                            elif line.startswith("PRENDA:"):
                                parsed["prenda"] = line.replace("PRENDA:", "").strip().lower()
                        return parsed
                    elif r.status_code == 429:
                        continue
                    else:
                        print(f"[Gemini] Error {r.status_code}: {r.text[:200]}")
            except Exception as e:
                print(f"[Gemini] Excepcion: {e}")
        return {"tipo": "otro", "nequi_ok": False, "monto": "", "anime": "no identificado", "prenda": "prenda"}

    async def analyze_client_image(self, raw: dict) -> dict:
        data = raw.get("data", {})
        message = data.get("message", {})
        caption = message.get("imageMessage", {}).get("caption", "")
        caption_lower = caption.lower()
        payment_words = ["transferencia exitosa", "comprobante", "ya pague", "hice el pago", "realice el pago", "transferi", "te mando el comprobante", "pague"]
        image_b64, mime = await self._download_image(raw)
        if image_b64:
            result = await self._gemini_analyze(image_b64, mime, caption)
            if result["tipo"] == "otro" and any(w in caption_lower for w in payment_words):
                result["tipo"] = "comprobante"
            return result
        print("[Analyze] No se pudo descargar la imagen, usando fallback por caption")
        if any(w in caption_lower for w in payment_words):
            return {"tipo": "comprobante", "nequi_ok": NEQUI_NUMBER in caption, "monto": "", "anime": "ninguno", "prenda": "ninguna"}
        return {"tipo": "prenda", "nequi_ok": False, "monto": "", "anime": "no identificado", "prenda": "prenda"}

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        if not evo_url:
            return
        reply_text = re.sub(r'\*+([^*]+)\*+', r'\1', message.text or "")
        reply_text = re.sub(r'_+([^_]+)_+', r'\1', reply_text).strip()
        headers = {"apikey": evo_key, "Content-Type": "application/json"}
        url = f"{evo_url}/message/sendText/{instance}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={"number": channel_user_id, "text": reply_text}, headers=headers)
            if resp.status_code not in (200, 201):
                print(f"[WhatsApp] Error: {resp.status_code} {resp.text[:100]}")
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
        msg = f"ONYX ALERTA - Cliente {channel_user_id}: {motivo}"
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json={"number": owner, "text": msg}, headers=headers)
            print(f"[WhatsApp] Alerta dueno enviada")