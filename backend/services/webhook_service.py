"""Service for webhook management"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import hashlib
import hmac
import json
import logging
from backend.services.execution_service import retry_with_backoff

logger = logging.getLogger(__name__)


class Webhook:
    """Represents a webhook configuration"""
    
    def __init__(
        self,
        webhook_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        retry_config: Optional[Dict[str, Any]] = None
    ):
        self.webhook_id = webhook_id
        self.url = url
        self.events = events
        self.secret = secret
        self.retry_config = retry_config or {"max_retries": 3, "backoff": "exponential"}
        self.created_at = datetime.utcnow()
    
    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload"""
        if not self.secret:
            return ""
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()


async def send_webhook(
    webhook: Webhook,
    event: str,
    payload: Dict[str, Any]
) -> bool:
    """
    Send webhook notification.
    
    Args:
        webhook: Webhook configuration
        event: Event type
        payload: Payload data
    
    Returns:
        True if successful, False otherwise
    """
    if event not in webhook.events:
        return False
    
    payload_json = json.dumps(payload)
    signature = webhook.generate_signature(payload_json)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event,
        "X-Webhook-ID": webhook.webhook_id
    }
    
    if signature:
        headers["X-Webhook-Signature"] = f"sha256={signature}"
    
    def _send():
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook.url, json=payload, headers=headers)
            response.raise_for_status()
            return True
    
    try:
        return retry_with_backoff(
            _send,
            max_retries=webhook.retry_config.get("max_retries", 3)
        )
    except Exception as e:
        logger.error(f"Failed to send webhook {webhook.webhook_id}: {e}")
        return False


def verify_webhook_signature(
    payload: str,
    signature: str,
    secret: str
) -> bool:
    """Verify webhook signature"""
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

