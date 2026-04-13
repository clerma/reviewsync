import logging

from config import settings
from providers.base import Review
from providers.google import GoogleReviewProvider
from providers.facebook import FacebookReviewProvider

logger = logging.getLogger(__name__)

REPLY_TEMPLATES = {
    "positive": (
        "Thank you so much for your wonderful review, {author}! "
        "We're thrilled to hear about your great experience. "
        "We look forward to serving you again!"
    ),
    "neutral": (
        "Thank you for your feedback, {author}. "
        "We appreciate you taking the time to share your experience. "
        "We're always looking to improve!"
    ),
    "negative": (
        "Thank you for your feedback, {author}. "
        "We're sorry to hear your experience didn't meet expectations. "
        "Please reach out to us directly so we can make things right."
    ),
}

PROVIDERS_WITH_REPLY = {
    "google": GoogleReviewProvider,
    "facebook": FacebookReviewProvider,
}


def _pick_template(rating: int) -> str:
    if rating >= 4:
        return REPLY_TEMPLATES["positive"]
    elif rating == 3:
        return REPLY_TEMPLATES["neutral"]
    else:
        return REPLY_TEMPLATES["negative"]


async def auto_respond(reviews: list[Review]):
    """Auto-respond to new reviews on platforms that support it."""
    if not settings.auto_respond_enabled:
        return

    for review in reviews:
        if review.reply:
            continue
        if review.platform not in PROVIDERS_WITH_REPLY:
            continue
        if review.rating < settings.auto_respond_min_rating and review.rating >= 4:
            continue

        template = _pick_template(review.rating)
        reply_text = template.format(author=review.author)

        try:
            provider = PROVIDERS_WITH_REPLY[review.platform]()
            await provider.post_reply(review.platform_review_id, reply_text)

            from providers.base import store
            store.update_reply(review.id, reply_text)

            logger.info(f"Auto-replied to {review.platform} review {review.id}")
        except Exception as e:
            logger.error(f"Failed to auto-reply to {review.id}: {e}")
