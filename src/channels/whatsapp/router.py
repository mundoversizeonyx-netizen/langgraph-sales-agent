"""WhatsApp webhook router para Evolution API."""
from fastapi import APIRouter, Request, BackgroundTasks
from src.channels.whatsapp.adapter import WhatsAppAdapter
from src.graphs.sales_graph import compile_sales_graph
from src.models.message import OutboundMessage
import traceback, re

router = APIRouter()
adapter = WhatsAppAdapter()
graph = compile_sales_graph()
_processed = set()

NEQUI_NUMBER = "3132721394"
PRECIOS = {"oversized": 90000, "polo": 90000, "buso": 130000}
NOMBRES = {"oversized": "camiseta oversized", "polo": "camiseta polo", "buso": "buso"}
ANIME_INVALIDOS = ["ninguno", "no identificado", "ninguna", "personaje y serie no identificados", "ninguno identificado", "nada", "personaje original, no identificado", "personaje no identificado / serie no identificada", ""]

def strip_markdown(text):
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'_+([^_]+)_+', r'\1', text)
    return text.strip()

async def process_message(payload: dict):
    try:
        data = payload.get("data", {})
        message = data.get("message", {})
        has_image = bool(message.get("imageMessage") or message.get("documentMessage"))
        inbound = adapter.parse_webhook(payload)
        client_text = (inbound.text or "").replace("[IMAGEN_CLIENTE]", "").strip()
        text_lower = (inbound.text or "").lower()

        if has_image:
            analysis = await adapter.analyze_client_image(payload)
            tipo = analysis.get("tipo", "otro")
            anime = analysis.get("anime", "")
            prenda = analysis.get("prenda", "")
            nequi_ok = analysis.get("nequi_ok", False)
            monto = analysis.get("monto", "")
            print("[Router] Imagen - tipo:" + tipo + " anime:" + anime + " prenda:" + prenda + " nequi_ok:" + str(nequi_ok) + " monto:" + monto)

            if tipo == "comprobante":
                cliente = inbound.channel_user_id
                if nequi_ok:
                    msg_dueno = "PAGO CONFIRMADO - Cliente " + cliente + " - Nequi " + NEQUI_NUMBER + " verificado. Monto: " + monto + ". Procesar pedido."
                    await adapter.notify_owner_direct(msg_dueno)
                    reply = "Perfecto, comprobante verificado al Nequi 3132721394. Tu pedido queda registrado y te avisamos cuando salga en los proximos 4 dias habiles."
                else:
                    msg_dueno = "REVISION MANUAL - Cliente " + cliente + " envio comprobante pero Nequi no coincide con " + NEQUI_NUMBER + ". Monto visible: " + monto
                    await adapter.notify_owner_direct(msg_dueno)
                    reply = "Recibo el comprobante, pero necesito confirmar que el pago fue al Nequi 3132721394. Verificalo y me cuentas."
                await adapter.send_reply(cliente, OutboundMessage(text=reply))
                return

            if tipo in ("oversized", "polo", "buso", "prenda"):
                tipo_prenda = prenda if prenda and prenda not in ("prenda", "ninguna", "") else "oversized"
                precio = PRECIOS.get(tipo_prenda, 90000)
                nombre_prenda = NOMBRES.get(tipo_prenda, "camiseta oversized")
                anime_clean = anime if anime and anime.lower() not in ANIME_INVALIDOS else None
                texto_extra = "El cliente ademas escribio: " + client_text + ". " if client_text else ""
                if anime_clean:
                    context = (
                        "El cliente envio una imagen de una " + nombre_prenda + " con estampado de " + anime_clean + ". "
                        + texto_extra
                        + "Confirma el tipo de prenda y menciona el personaje para conectar con el cliente. "
                        + "Dile que el precio es " + str(precio) + " COP con envio incluido y pregunta la talla (S M L XL). "
                        + "Maximo 2 oraciones. Sin asteriscos ni markdown."
                    )
                else:
                    context = (
                        "El cliente envio una imagen de una " + nombre_prenda + ". "
                        + texto_extra
                        + "Confirma el tipo de prenda y dile que el precio es " + str(precio) + " COP con envio incluido. "
                        + "Preguntale de que personaje o serie es el diseno para asesorarlo mejor. "
                        + "Maximo 2 oraciones. Sin asteriscos ni markdown."
                    )
                user_input = context
            else:
                if not client_text:
                    reply = "No identifique bien la imagen. Cuentame que diseno de ONYX te gusto."
                    await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply))
                    return
                user_input = client_text

        else:
            if not inbound.text or not inbound.text.strip():
                return
            payment_hints = ["comprobante", "te envio", "ya pague", "hice el pago", "transferencia", "te mando el pago", "envio el pago"]
            if any(w in text_lower for w in payment_hints):
                user_input = (
                    "El cliente indica que va a enviar el comprobante de pago. "
                    "Confirma que lo recibes y pidele que adjunte la imagen aqui en el chat. "
                    "Una sola oracion natural, sin markdown."
                )
            else:
                user_input = inbound.text

        print("[Router] Input: " + user_input[:120])
        result = await graph.ainvoke(
            {"messages": [("user", user_input)]},
            config={"configurable": {"thread_id": inbound.thread_id, "tenant_id": inbound.tenant_id}}
        )
        reply_text = strip_markdown(result["messages"][-1].content)
        print("[Router] Respuesta: " + reply_text[:100])
        await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply_text))

    except Exception as e:
        print("[Router] ERROR: " + str(e))
        print(traceback.format_exc())

@router.post("")
@router.post("/{event_name}")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks, event_name: str = ""):
    payload = await request.json()
    event = payload.get("event", "") or event_name.replace("-", ".")
    if event != "messages.upsert":
        return {"status": "ignored"}
    if payload.get("data", {}).get("key", {}).get("fromMe", False):
        return {"status": "ignored"}
    msg_id = payload.get("data", {}).get("key", {}).get("id", "")
    if msg_id and msg_id in _processed:
        return {"status": "ignored"}
    if msg_id:
        _processed.add(msg_id)
        if len(_processed) > 1000:
            _processed.clear()
    background_tasks.add_task(process_message, payload)
    return {"status": "ok"}