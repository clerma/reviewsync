import logging
import uuid
from datetime import datetime, timezone

from providers.base import BaseReviewProvider, Review, store

logger = logging.getLogger(__name__)


class WebsiteReviewProvider(BaseReviewProvider):
    platform_name = "website"
    supports_reply = True

    async def fetch_reviews(self) -> list[Review]:
        return store.get_by_platform("website")

    async def submit_review(self, author: str, rating: int, text: str) -> Review:
        review_id = str(uuid.uuid4())[:12]
        review = Review(
            id=f"website_{review_id}",
            platform="website",
            author=author,
            rating=rating,
            text=text,
            date=datetime.now(timezone.utc),
            platform_review_id=review_id,
        )
        store.add(review)
        logger.info(f"New website review from {author}: {rating} stars")
        return review

    async def post_reply(self, review_id: str, text: str) -> bool:
        success = store.update_reply(review_id, text)
        if success:
            logger.info(f"Replied to website review {review_id}")
        return success
