"""Instagram webhook router."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

from src.channels.instagram.adapter import InstagramAdapter

router = APIRouter()
adapter = InstagramAdapter()


@router.get("", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Instagram webhook verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == "your_verify_token_here":
        return challenge
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
async def receive_webhook(request: Request):
    payload = await request.json()
    inbound_msg = adapter.parse_webhook(payload)
    
    # Process graph...
    
    return {"status": "ok"}
