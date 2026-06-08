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

NEQUI_NUMBER = "3132721394"

async def process_message(payload: dict):
    try:
        data = payload.get("data", {})
        message = data.get("message", {})
        has_image = bool(message.get("imageMessage") or message.get("documentMessage"))
        inbound = adapter.parse_webhook(payload)
        client_text = (inbound.text or "").replace("[IMAGEN_CLIENTE]", "").strip()
        client_text_lower = client_text.lower()

        if has_image:
            analysis = await adapter.analyze_client_image(payload)
            tipo = analysis.get("tipo", "otro")
            anime = analysis.get("anime", "")
            prenda = analysis.get("prenda", "")
            nequi_ok = analysis.get("nequi_ok", False)
            monto = analysis.get("monto", "")
            print(f"[Router] Imagen - tipo:{tipo} anime:{anime} prenda:{prenda} nequi_ok:{nequi_ok} monto:{monto}")

            if tipo == "comprobante":
                if nequi_ok:
                    await adapter.notify_owner(
                        inbound.channel_user_id,
                        f"PAGO CONFIRMADO - Nequi {NEQUI_NUMBER} verificado. Monto: {monto}. Revisa el chat para procesar el pedido."
                    )
                    reply = "Perfecto, comprobante verificado al Nequi 3132721394. Tu pedido queda registrado y lo despachamos en 4 dias habiles, te avisamos cuando salga."
                else:
                    await adapter.notify_owner(
                        inbound.channel_user_id,
                        f"ALERTA - Cliente envio comprobante pero el numero Nequi no coincide con {NEQUI_NUMBER}. Revisar manualmente."
                    )
                    reply = "Recibo el comprobante, pero necesito verificar que el pago sea al Nequi 3132721394. Confirma que enviaste al numero correcto."
                await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply))
                return

            if tipo in ("oversized", "polo", "buso", "prenda"):
                anime_info = f"personaje/anime identificado: {anime}" if anime and anime.lower() not in ("ninguno", "no identificado", "") else "anime no identificado en la imagen"
                context = (
                    f"El cliente envio una captura de una camiseta tipo {prenda}. "
                    f"Gemini identifico: {anime_info}. "
                    f"{'El cliente escribio: ' + client_text + '. ' if client_text else ''}"
                    f"Pregunta la talla para confirmar el pedido. No ofrezcas enviar fotos. No uses markdown ni asteriscos."
                )
                user_input = context
            else:
                if not client_text:
                    reply = "Recibido, pero no identifique bien la imagen. Cual diseno te gusto del Instagram de ONYX?"
                    await adapter.send_reply(inbound.channel_user_id, OutboundMessage(text=reply))
                    return
                user_input = client_text
        else:
            if not inbound.text or not inbound.text.strip():
                return
            user_input = inbound.text

        print(f"[Router] Input: {user_input[:120]}")
        result = await graph.ainvoke(
            {"messages": [("user", user_input)]},
            config={"configurable": {"thread_id": inbound.thread_id, "tenant_id": inbound.tenant_id}}
        )
        reply_text = result["messages"][-1].content
        import re
        reply_text = re.sub(r'\*+([^*]+)\*+', r'\1', reply_text)
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