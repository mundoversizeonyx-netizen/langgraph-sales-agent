"""WhatsApp webhook router para Evolution API."""
from fastapi import APIRouter, Request, BackgroundTasks
from src.channels.whatsapp.adapter import WhatsAppAdapter
from src.graphs.sales_graph import compile_sales_graph
from src.models.message import OutboundMessage
import asyncio

router = APIRouter()
adapter = WhatsAppAdapter()
graph = compile_sales_graph()

async def process_message(payload: dict):
    inbound = adapter.parse_webhook(payload)
    if not inbound.text:
        return
    result = await graph.ainvoke(
        {"messages": [("user", inbound.text)]},
        config={"configurable": {
            "thread_id": inbound.thread_id,
            "tenant_id": inbound.tenant_id
        }}
    )
    reply_text = result["messages"][-1].content
    outbound = OutboundMessage(text=reply_text)
    await adapter.send_reply(inbound.channel_user_id, outbound)

@router.post("")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    event = payload.get("event", "")
    if event == "messages.upsert" and not payload.get("data", {}).get("key", {}).get("fromMe", False):
        background_tasks.add_task(process_message, payload)
    return {"status": "ok"}
