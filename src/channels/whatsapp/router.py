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

        if has_image:
            cliente = inbound.channel_user_id
            await adapter.notify_owner_direct(
                "ONYX - Cliente " + cliente + " envio una imagen. Entra al chat para cerrar la venta."
            )
            reply = "Que talla necesitas?"
            await adapter.send_reply(cliente, OutboundMessage(text=reply))
            return

        if not inbound.text or not inbound.text.strip():
            return

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