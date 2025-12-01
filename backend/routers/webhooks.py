"""Webhook router"""
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from typing import Optional
from backend.database import get_session
from sqlmodel import Session
from backend.services.webhook_service import verify_webhook_signature
import json

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/incoming")
async def receive_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_event: Optional[str] = Header(None)
):
    """Receive incoming webhook"""
    body = await request.body()
    payload = json.loads(body.decode())
    
    # Verify signature if provided
    if x_webhook_signature:
        # In production, get secret from configuration
        secret = "webhook_secret"  # Should be from config
        if not verify_webhook_signature(body.decode(), x_webhook_signature, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Process webhook
    event_type = x_webhook_event or "unknown"
    
    return {
        "status": "received",
        "event": event_type,
        "payload": payload
    }

