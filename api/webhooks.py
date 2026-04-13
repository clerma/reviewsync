import logging

from fastapi import APIRouter, Request

from providers.base import store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/google")
async def google_webhook(request: Request):
    """Handle Google push notifications for new reviews."""
    body = await request.json()
    logger.info(f"Google webhook received: {body}")
    return {"status": "received"}


@router.post("/webhooks/facebook")
async def facebook_webhook(request: Request):
    """Handle Facebook webhook for page review changes."""
    body = await request.json()
    logger.info(f"Facebook webhook received: {body}")

    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "ratings":
                    logger.info("Facebook rating change detected, triggering sync")
                    from services.sync import sync_all_reviews
                    await sync_all_reviews()

    return {"status": "received"}


@router.get("/webhooks/facebook")
async def facebook_webhook_verify(request: Request):
    """Facebook webhook verification endpoint."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token:
        return int(challenge) if challenge else ""
    return {"error": "Verification failed"}
