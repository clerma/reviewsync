import logging
from email.mime.text import MIMEText

import httpx

from config import settings
from providers.base import Review

logger = logging.getLogger(__name__)


async def notify_new_reviews(reviews: list[Review]):
    """Send notifications for new reviews via webhook and/or email."""
    if not reviews:
        return

    if settings.webhook_url:
        await _send_webhook(reviews)

    if settings.smtp_host and settings.notify_email:
        await _send_email(reviews)


async def _send_webhook(reviews: list[Review]):
    payload = {
        "event": "new_reviews",
        "count": len(reviews),
        "reviews": [
            {
                "id": r.id,
                "platform": r.platform,
                "author": r.author,
                "rating": r.rating,
                "text": r.text[:200],
                "date": r.date.isoformat(),
            }
            for r in reviews
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.webhook_url,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        logger.info(f"Webhook sent: {len(reviews)} new reviews")
    except Exception as e:
        logger.error(f"Webhook failed: {e}")


async def _send_email(reviews: list[Review]):
    try:
        import aiosmtplib

        subject = f"New Reviews Alert: {len(reviews)} new review(s)"
        lines = []
        for r in reviews:
            stars = "\u2605" * r.rating + "\u2606" * (5 - r.rating)
            lines.append(f"[{r.platform.upper()}] {r.author} - {stars}")
            if r.text:
                lines.append(f"  \"{r.text[:150]}\"")
            lines.append("")

        body = "\n".join(lines)
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user
        msg["To"] = settings.notify_email

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
        )
        logger.info(f"Email sent to {settings.notify_email}")
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
