"""WhatsApp adapter - OpenRouter vision principal, Gemini fallback."""
from datetime import datetime, timezone
import httpx, os, re

from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage

NEQUI_NUMBER = "3132721394"

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
        final_text = "[IMAGEN_CLIENTE]" + text if has_image else text
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
                    evo_url + "/chat/getBase64FromMediaMessage/" + instance,
                    json=body,
                    headers={"apikey": evo_key, "Content-Type": "application/json"}
                )
                print("[Download] Status: " + str(r.status_code))
                if r.status_code in (200, 201):
                    resp = r.json()
                    b64 = resp.get("base64", "") or resp.get("data", "")
                    if b64:
                        if "base64," in b64:
                            b64 = b64.split("base64,")[1]
                        print("[Download] OK bytes: " + str(len(b64)))
                        return b64, mime
                    print("[Download] Sin base64: " + str(list(resp.keys())))
                else:
                    print("[Download] Error: " + str(r.status_code))
        except Exception as e:
            print("[Download] Excepcion: " + str(e))
        return None, mime

    def _build_prompt(self) -> str:
        return (
            "Analiza esta imagen. Determina si es comprobante de pago o prenda de ropa.\n\n"
            "Si ves transferencia bancaria, recibo, pantalla Nequi, Bancolombia, valor en pesos:\n"
            "TIPO: comprobante\n"
            "NEQUI_OK: si (solo si aparece el numero " + NEQUI_NUMBER + ") o no\n"
            "MONTO: [valor exacto visible]\n"
            "ANIME: ninguno\n"
            "PRENDA: ninguna\n\n"
            "Si ves camiseta, buso o polo con estampado de anime:\n"
            "TIPO: prenda\n"
            "NEQUI_OK: no\n"
            "MONTO: ninguno\n"
            "ANIME: [personaje y serie del estampado, o no identificado]\n"
            "PRENDA: [oversized | polo | buso]\n\n"
            "Otra cosa:\n"
            "TIPO: otro\nNEQUI_OK: no\nMONTO: ninguno\nANIME: ninguno\nPRENDA: ninguna\n\n"
            "Responde SOLO las 5 lineas. Nada mas."
        )

    def _parse_vision_response(self, text: str) -> dict:
        parsed = {"tipo": "otro", "nequi_ok": False, "monto": "", "anime": "no identificado", "prenda": "prenda"}
        for line in text.strip().split("\n"):
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

    async def _openrouter_analyze(self, image_b64: str, mime: str) -> dict:
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        if not or_key:
            print("[OpenRouter] No hay key configurada")
            return None
        prompt = self._build_prompt()
        body = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + image_b64}}
                ]
            }]
        }
        try:
            print("[OpenRouter] Llamando gemini-2.0-flash-exp:free...")
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=body,
                    headers={
                        "Authorization": "Bearer " + or_key,
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://onyx.store",
                        "X-Title": "ONYX Sofia"
                    }
                )
                print("[OpenRouter] Status: " + str(r.status_code))
                if r.status_code == 200:
                    out = r.json()["choices"][0]["message"]["content"].strip()
                    print("[OpenRouter] Resultado: " + out)
                    return self._parse_vision_response(out)
                else:
                    print("[OpenRouter] Error: " + r.text[:300])
                    return None
        except Exception as e:
            print("[OpenRouter] Excepcion: " + str(e))
            return None

    async def _gemini_analyze(self, image_b64: str, mime: str) -> dict:
        keys = [
            os.getenv("GEMINI_API_KEY", ""),
            os.getenv("GEMINI_API_KEY_2", ""),
            os.getenv("GEMINI_API_KEY_3", ""),
            os.getenv("GEMINI_API_KEY_4", ""),
            os.getenv("GEMINI_API_KEY_5", ""),
            os.getenv("GEMINI_API_KEY_6", "")
        ]
        keys = [k for k in keys if k]
        print("[Gemini] Keys: " + str(len(keys)))
        prompt = self._build_prompt()
        body = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": image_b64}}
                ]
            }]
        }
        for k in keys:
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + k
                print("[Gemini] Llamando key: " + k[:15] + "...")
                async with httpx.AsyncClient(timeout=25) as client:
                    r = await client.post(url, json=body)
                    print("[Gemini] Status: " + str(r.status_code))
                    if r.status_code in (200, 201):
                        out = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        print("[Gemini] Resultado: " + out)
                        return self._parse_vision_response(out)
                    elif r.status_code == 429:
                        print("[Gemini] 429 siguiente key...")
                        continue
                    else:
                        print("[Gemini] Error: " + r.text[:200])
            except Exception as e:
                print("[Gemini] Excepcion: " + str(e))
        return None

    async def analyze_client_image(self, raw: dict) -> dict:
        data = raw.get("data", {})
        message = data.get("message", {})
        caption = message.get("imageMessage", {}).get("caption", "")
        caption_lower = caption.lower()
        payment_words = ["transferencia", "comprobante", "ya pague", "hice el pago", "realice el pago", "transferi", "te mando", "pague", "envio el pago"]
        fallback = {"tipo": "prenda", "nequi_ok": False, "monto": "", "anime": "no identificado", "prenda": "prenda"}

        image_b64, mime = await self._download_image(raw)
        if not image_b64:
            print("[Analyze] Sin imagen, fallback caption")
            if any(w in caption_lower for w in payment_words):
                return {"tipo": "comprobante", "nequi_ok": NEQUI_NUMBER in caption, "monto": "", "anime": "ninguno", "prenda": "ninguna"}
            return fallback

        # OpenRouter primero
        result = await self._openrouter_analyze(image_b64, mime)

        # Gemini como fallback
        if result is None:
            print("[Analyze] OpenRouter fallo, intentando Gemini...")
            result = await self._gemini_analyze(image_b64, mime)

        if result is None:
            print("[Analyze] Todo fallo, fallback caption")
            if any(w in caption_lower for w in payment_words):
                return {"tipo": "comprobante", "nequi_ok": NEQUI_NUMBER in caption, "monto": "", "anime": "ninguno", "prenda": "ninguna"}
            return fallback

        if result["tipo"] == "otro" and any(w in caption_lower for w in payment_words):
            result["tipo"] = "comprobante"
            result["nequi_ok"] = NEQUI_NUMBER in caption

        return result

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        if not evo_url:
            return
        reply_text = re.sub(r'\*+([^*]+)\*+', r'\1', message.text or "")
        reply_text = re.sub(r'_+([^_]+)_+', r'\1', reply_text).strip()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                evo_url + "/message/sendText/" + instance,
                json={"number": channel_user_id, "text": reply_text},
                headers={"apikey": evo_key, "Content-Type": "application/json"}
            )
            if resp.status_code not in (200, 201):
                print("[WhatsApp] Error: " + str(resp.status_code))
            else:
                print("[WhatsApp] OK: " + reply_text[:80])

    async def notify_owner(self, channel_user_id: str, motivo: str) -> None:
        evo_url = os.getenv("EVOLUTION_URL", "")
        evo_key = os.getenv("EVOLUTION_API_KEY", "")
        instance = os.getenv("EVOLUTION_INSTANCE", "demo")
        owner = os.getenv("OWNER_NUMBER", "573043898187")
        if not evo_url:
            return
        msg = "ONYX ALERTA - Cliente " + channel_user_id + ": " + motivo
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                evo_url + "/message/sendText/" + instance,
                json={"number": owner, "text": msg},
                headers={"apikey": evo_key, "Content-Type": "application/json"}
            )
            print("[WhatsApp] Alerta dueno enviada")