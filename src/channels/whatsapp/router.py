"""WhatsApp webhook router para Evolution API."""
from fastapi import APIRouter, Request, BackgroundTasks
from src.channels.whatsapp.adapter import WhatsAppAdapter
from src.graphs.sales_graph import compile_sales_graph
from src.models.message import OutboundMessage
import traceback

router = APIRouter()
adapter = WhatsAppAdapter()
graph = compile_sales_graph()
_processed = set()

PAYMENT_WORDS = ["ya pague", "ya pago", "hice el pago", "realice el pago", "te mando el comprobante", "te envio el comprobante", "comprobante enviado", "pague", "transferi"]

async def process_message(payload: dict):
    try:
        data = payload.get("data", {})
        message = data.get("message", {})
        has_image = bool(message.get("imageMessage") or message.get("documentMessage"))
        inbound = adapter.parse_webhook(payload)
        client_text = (inbound.text or "").lower().replace("[imagen]", "").strip()

        if has_image:
            image_type = await adapter.handle_image_message(payload)
            if image_type == "comprobante" or any(w in client_text for w in PAYMENT_WORDS):
                await adapter.notify_owner(inbound.channel_user_id, "envio comprobante de pago")
                reply = "Perfecto, recibido. Tu pedido queda en proceso y lo despachamos en 4 dias habiles."
                await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply))
                return
            else:
                if not client_text:
                    return
        
        if not inbound.text or inbound.text == "[IMAGEN]":
            return

        print(f"[Router] Mensaje de {inbound.channel_user_id}: {client_text or inbound.text}")
        result = await graph.ainvoke(
            {"messages": [("user", client_text or inbound.text)]},
            config={"configurable": {"thread_id": inbound.thread_id, "tenant_id": inbound.tenant_id}}
        )
        reply_text = result["messages"][-1].content
        print(f"[Router] Respuesta: {reply_text[:100]}")
        await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply_text))
    except Exception as e:
        print(f"[Router] ERROR: {e}")
        print(traceback.format_exc())

@router.post("")
@router.post("/{event_name}")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks, event_name: str = ""):
    payload = await request.json()
    event = payload.get("event", "") or event_name.replace("-", ".")
    if event != "messages.upsert":
        return {"status": "ignored"}
    from_me = payload.get("data", {}).get("key", {}).get("fromMe", False)
    if from_me:
        return {"status": "ignored"}
    msg_id = payload.get("data", {}).get("key", {}).get("id", "")
    if msg_id and msg_id in _processed:
        print(f"[Router] Duplicado ignorado: {msg_id}")
        return {"status": "ignored"}
    if msg_id:
        _processed.add(msg_id)
        if len(_processed) > 1000:
            _processed.clear()
    print(f"[Router] Procesando mensaje entrante")
    background_tasks.add_task(process_message, payload)
    return {"status": "ok"}