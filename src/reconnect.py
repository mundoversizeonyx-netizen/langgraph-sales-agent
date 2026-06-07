"""Auto-reconnect endpoint para Evolution API."""
import os, httpx, asyncio

EVO_URL = os.getenv("EVOLUTION_URL", "")
EVO_KEY = os.getenv("EVOLUTION_API_KEY", "")
AGENT_URL = os.getenv("AGENT_URL", "https://langgraph-sales-agent.onrender.com")
INSTANCE = os.getenv("EVOLUTION_INSTANCE", "demo")

async def ensure_instance_connected():
    if not EVO_URL:
        return
    headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{EVO_URL}/instance/fetchInstances", headers={"apikey": EVO_KEY})
            data = r.json()
            instances = data if isinstance(data, list) else data.get("value", [])
            connected = any(
                i.get("name") == INSTANCE and i.get("connectionStatus") == "open"
                for i in instances
            )
            if connected:
                print(f"[Reconnect] Instancia {INSTANCE} OK")
                await client.post(f"{EVO_URL}/webhook/set/{INSTANCE}", headers=headers, json={
                    "webhook": {
                        "enabled": True,
                        "url": f"{AGENT_URL}/webhooks/whatsapp",
                        "webhook_by_events": True,
                        "webhook_base64": False,
                        "events": ["MESSAGES_UPSERT"]
                    }
                }, timeout=10)
                print(f"[Reconnect] Webhook verificado OK")
            else:
                print(f"[Reconnect] Instancia desconectada — reconexion manual requerida")
    except Exception as e:
        print(f"[Reconnect] Error: {e}")