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

async def process_message(payload: dict):
    try:
        data = payload.get("data", {})
        message = data.get("message", {})
        has_image = bool(message.get("imageMessage") or message.get("documentMessage"))
        inbound = adapter.parse_webhook(payload)
        client_text = (inbound.text or "").replace("[IMAGEN_CLIENTE]", "").strip()

        if has_image:
            analysis = await adapter.analyze_client_image(payload)
            tipo = analysis.get("tipo", "otro")
            detalle = analysis.get("detalle", "")
            print(f"[Router] Imagen analizada - tipo: {tipo} | detalle: {detalle}")

            if tipo == "comprobante":
                await adapter.notify_owner(inbound.channel_user_id, "envio comprobante de pago")
                reply = "Listo, recibido el comprobante. Tu pedido queda registrado y lo despachamos en 4 dias habiles, te avisamos cuando salga."
                await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply))
                return

            if tipo == "prenda":
                context = f"El cliente envio una imagen de una prenda. Lo que Gemini identifico en la imagen: {detalle}. "
                if client_text:
                    context += f"El cliente tambien escribio: {client_text}. "
                context += "Usa esta informacion para asesorar al cliente sobre el producto de ONYX mas similar o confirmar su pedido si ya eligio talla."
                user_input = context
            else:
                if not client_text:
                    reply = "Recibido, pero no logre identificar bien la imagen. Cuentame que prenda te interesa y en que talla."
                    await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply))
                    return
                user_input = client_text
        else:
            if not inbound.text or not inbound.text.strip():
                return
            user_input = inbound.text

        print(f"[Router] Procesando: {user_input[:100]}")
        result = await graph.ainvoke(
            {"messages": [("user", user_input)]},
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
    background_tasks.add_task(process_message, payload)
    return {"status": "ok"}