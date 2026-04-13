import logging
from datetime import datetime, timezone

import httpx

from config import settings
from providers.base import BaseReviewProvider, Review

logger = logging.getLogger(__name__)

YELP_BASE = "https://api.yelp.com/v3"


class YelpReviewProvider(BaseReviewProvider):
    platform_name = "yelp"
    supports_reply = False

    def __init__(self):
        self.api_key = settings.yelp_api_key
        self.business_id = settings.yelp_business_id

    async def fetch_reviews(self) -> list[Review]:
        if not self.api_key or not self.business_id:
            logger.warning("Yelp provider not configured, skipping")
            return []

        url = f"{YELP_BASE}/businesses/{self.business_id}/reviews"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"limit": 50, "sort_by": "newest"}

        reviews = []

        async with httpx.AsyncClient() as client:
            offset = 0
            while True:
                params["offset"] = offset
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                batch = data.get("reviews", [])
                if not batch:
                    break

                for r in batch:
                    review_id = r.get("id", "")
                    user = r.get("user", {})
                    time_created = r.get("time_created", "")

                    try:
                        date = datetime.strptime(time_created, "%Y-%m-%d %H:%M:%S")
                        date = date.replace(tzinfo=timezone.utc)
                    except (ValueError, AttributeError):
                        date = datetime.now(timezone.utc)

                    reviews.append(Review(
                        id=f"yelp_{review_id}",
                        platform="yelp",
                        author=user.get("name", "Yelp User"),
                        rating=r.get("rating", 5),
                        text=r.get("text", ""),
                        date=date,
                        platform_review_id=review_id,
                        metadata={
                            "profile_url": user.get("profile_url", ""),
                            "image_url": user.get("image_url", ""),
                            "url": r.get("url", ""),
                        },
                    ))

                offset += len(batch)
                if len(batch) < 50:
                    break

        logger.info(f"Fetched {len(reviews)} Yelp reviews")
        return reviews
