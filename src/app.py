"""Application entry point.

Mounts all channel routers into a single FastAPI app.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.channels.web.router import router as web_router
from src.channels.whatsapp.router import router as whatsapp_router
from src.channels.telegram.router import router as telegram_router
from src.channels.instagram.router import router as instagram_router

app = FastAPI(title="Multi-Channel Sales Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Web endpoints at root (for the Sales Studio)
app.include_router(web_router, prefix="")

# Webhooks
app.include_router(whatsapp_router, prefix="/webhooks/whatsapp")
app.include_router(telegram_router, prefix="/webhooks/telegram")
app.include_router(instagram_router, prefix="/webhooks/instagram")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Sales Agent (Multi-Channel) starting on http://localhost:3000")
    uvicorn.run("src.app:app", host="0.0.0.0", port=3000, reload=False)
