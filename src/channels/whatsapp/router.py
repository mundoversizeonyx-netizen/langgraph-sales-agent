"""WhatsApp webhook router para Evolution API."""
from fastapi import APIRouter, Request, BackgroundTasks
from src.channels.whatsapp.adapter import WhatsAppAdapter
from src.graphs.sales_graph import compile_sales_graph
from src.models.message import OutboundMessage
import traceback

router = APIRouter()
adapter = WhatsAppAdapter()
graph = compile_sales_graph()

async def process_message(payload: dict):
    try:
        inbound = adapter.parse_webhook(payload)
        print(f"[Router] Mensaje de {inbound.channel_user_id}: {inbound.text}")
        if not inbound.text:
            print("[Router] Texto vacio, ignorando")
            return
        result = await graph.ainvoke(
            {"messages": [("user", inbound.text)]},
            config={"configurable": {
                "thread_id": inbound.thread_id,
                "tenant_id": inbound.tenant_id
            }}
        )
        reply_text = result["messages"][-1].content
        print(f"[Router] Respuesta generada: {reply_text[:100]}")
        outbound = OutboundMessage(text=reply_text)
        await adapter.send_reply(inbound.channel_user_id, outbound)
    except Exception as e:
        print(f"[Router] ERROR CRITICO: {e}")
        print(traceback.format_exc())

@router.post("")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    event = payload.get("event", "")
    print(f"[Router] Evento recibido: {event}")
    if event == "messages.upsert" and not payload.get("data", {}).get("key", {}).get("fromMe", False):
        background_tasks.add_task(process_message, payload)
    return {"status": "ok"}