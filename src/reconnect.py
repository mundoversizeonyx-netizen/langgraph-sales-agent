"""Auto-reconnect endpoint para Evolution API."""
import os, httpx, asyncio

EVO_URL = os.getenv("EVOLUTION_URL", "")
EVO_KEY = os.getenv("EVOLUTION_API_KEY", "")
AGENT_URL = os.getenv("AGENT_URL", "https://langgraph-sales-agent.onrender.com")
INSTANCE = os.getenv("EVOLUTION_INSTANCE", "demo")

async def ensure_instance_connected():
    """Verifica y reconecta la instancia si es necesario."""
    if not EVO_URL:
        return
    headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{EVO_URL}/instance/fetchInstances", headers={"apikey": EVO_KEY})
            instances = r.json()
            exists = any(
                i.get("name") == INSTANCE and i.get("connectionStatus") == "open"
                for i in (instances if isinstance(instances, list) else instances.get("value", []))
            )
            if exists:
                print(f"[Reconnect] Instancia {INSTANCE} conectada OK")
                return
            print(f"[Reconnect] Instancia desconectada — reconectando...")
            try:
                await client.delete(f"{EVO_URL}/instance/delete/{INSTANCE}", headers=headers, timeout=10)
            except:
                pass
            await asyncio.sleep(2)
            await client.post(f"{EVO_URL}/instance/create", headers=headers, json={
                "instanceName": INSTANCE, "qrcode": False, "integration": "WHATSAPP-BAILEYS"
            }, timeout=15)
            await asyncio.sleep(2)
            await client.post(f"{EVO_URL}/webhook/set/{INSTANCE}", headers=headers, json={
                "webhook": {
                    "enabled": True,
                    "url": f"{AGENT_URL}/webhooks/whatsapp",
                    "webhook_by_events": True,
                    "webhook_base64": False,
                    "events": ["MESSAGES_UPSERT"]
                }
            }, timeout=15)
            print(f"[Reconnect] Instancia recreada — escanear QR necesario")
    except Exception as e:
        print(f"[Reconnect] Error: {e}")