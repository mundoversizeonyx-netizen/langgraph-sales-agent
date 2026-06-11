"""WhatsApp adapter - Qwen VL via OpenRouter (vision OCR definitivo)."""
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
                    print("[Download] Error: " + str(r.status_code) + " " + r.text[:100])
        except Exception as e:
            print("[Download] Excepcion: " + str(e))
        return None, mime

    def _build_prompt(self) -> str:
        return (
            "Analiza esta imagen con OCR completo. Lee todo el texto visible.\n\n"
            "Si la imagen muestra transferencia bancaria, recibo de pago, pantalla Nequi, Bancolombia, valor en pesos colombianos, o cualquier comprobante de pago:\n"
            "TIPO: comprobante\n"
            "NEQUI_OK: si (solo si el numero " + NEQUI_NUMBER + " aparece en la imagen) o no\n"
            "MONTO: [valor exacto visible en la imagen, ej: 150000]\n"
            "ANIME: ninguno\n"
            "PRENDA: ninguna\n\n"
            "Si la imagen muestra ropa con estampado de anime (camiseta, buso, polo):\n"
            "TIPO: prenda\n"
            "NEQUI_OK: no\n"
            "MONTO: ninguno\n"
            "ANIME: [personaje y serie exactos, o no identificado]\n"
            "PRENDA: [oversized | polo | buso]\n\n"
            "Cualquier otra cosa:\n"
            "TIPO: otro\nNEQUI_OK: no\nMONTO: ninguno\nANIME: ninguno\nPRENDA: ninguna\n\n"
            "Responde UNICAMENTE las 5 lineas. Nada mas."
        )

    def _parse_result(self, text: str) -> dict:
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

    async def _vision_analyze(self, image_b64: str, mime: str) -> dict:
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        if not or_key:
            print("[Vision] ERROR: Sin OPENROUTER_API_KEY")
            return None
        prompt = self._build_prompt()
        data_uri = "data:" + mime + ";base64," + image_b64
        models = [
            "qwen/qwen2.5-vl-72b-instruct:free",
            "qwen/qwen2.5-vl-32b-instruct:free",
            "meta-llama/llama-4-maverick:free",
            "google/gemma-3-27b-it:free"
        ]
        for model in models:
            try:
                body = {
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}}
                        ]
                    }],
                    "max_tokens": 150
                }
                print("[Vision] Llamando: " + model)
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
                    print("[Vision] Status: " + str(r.status_code))
                    if r.status_code == 200:
                        resp = r.json()
                        out = resp["choices"][0]["message"]["content"].strip()
                        print("[Vision] Resultado: " + out)
                        return self._parse_result(out)
                    elif r.status_code == 429:
                        print("[Vision] 429 en " + model + ", probando siguiente...")
                        continue
                    else:
                        print("[Vision] Error " + str(r.status_code) + ": " + r.text[:200])
                        continue
            except Exception as e:
                print("[Vision] Excepcion en " + model + ": " + str(e))
                continue
        print("[Vision] Todos los modelos fallaron")
        return None

    async def analyze_client_image(self, raw: dict) -> dict:
        data = raw.get("data", {})
        message = data.get("message", {})
        caption = message.get("imageMessage", {}).get("caption", "")
        caption_lower = caption.lower()
        payment_words = ["transferencia", "comprobante", "ya pague", "hice el pago", "realice el pago", "transferi", "te mando", "pague", "envio el pago"]
        fallback_pago = {"tipo": "comprobante", "nequi_ok": NEQUI_NUMBER in caption, "monto": "", "anime": "ninguno", "prenda": "ninguna"}
        fallback_prenda = {"tipo": "prenda", "nequi_ok": False, "monto": "", "anime": "no identificado", "prenda": "prenda"}

        image_b64, mime = await self._download_image(raw)
        if not image_b64:
            print("[Analyze] Sin imagen descargada")
            if any(w in caption_lower for w in payment_words):
                return fallback_pago
            return fallback_prenda

        result = await self._vision_analyze(image_b64, mime)

        if result is None:
            print("[Analyze] Vision fallo, usando fallback caption")
            if any(w in caption_lower for w in payment_words):
                return fallback_pago
            return fallback_prenda

        if result["tipo"] == "otro" and any(w in caption_lower for w in payment_words):
            result["tipo"] = "comprobante"
            result["nequi_ok"] = NEQUI_NUMBER in caption

        print("[Analyze] Final: " + str(result))
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