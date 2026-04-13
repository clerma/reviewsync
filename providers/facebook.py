import logging
from datetime import datetime, timezone

import httpx

from config import settings
from providers.base import BaseReviewProvider, Review

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v25.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class FacebookReviewProvider(BaseReviewProvider):
    platform_name = "facebook"
    supports_reply = True

    def __init__(self):
        self.page_id = settings.facebook_page_id
        self._user_token = settings.facebook_page_access_token
        self._page_token = None

    async def _get_page_token(self) -> str:
        """Exchange user token for a page access token if needed."""
        if self._page_token:
            return self._page_token

        # Try using the token directly first — if it's already a page token, great
        # Otherwise exchange user token → page token via the API
        url = f"{GRAPH_BASE}/{self.page_id}"
        params = {"fields": "access_token", "access_token": self._user_token}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                self._page_token = data.get("access_token", self._user_token)
                logger.info("Exchanged user token for page access token")
            else:
                # Token might already be a page token
                self._page_token = self._user_token
                logger.info("Using provided token as page access token")

        return self._page_token

    async def fetch_reviews(self) -> list[Review]:
        if not self.page_id or not self._user_token:
            logger.warning("Facebook provider not configured, skipping")
            return []

        page_token = await self._get_page_token()

        url = f"{GRAPH_BASE}/{self.page_id}/ratings"
        params = {
            "access_token": page_token,
            "fields": "reviewer{name,id},created_time,rating,review_text,recommendation_type,open_graph_story{id}",
            "limit": 100,
        }

        reviews = []

        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                for r in data.get("data", []):
                    reviewer = r.get("reviewer", {})
                    review_id = r.get("open_graph_story", {}).get("id", "")
                    if not review_id:
                        review_id = f"{reviewer.get('id', 'unknown')}_{r.get('created_time', '')}"

                    rating = r.get("rating")
                    if rating is None:
                        rec = r.get("recommendation_type", "")
                        rating = 5 if rec == "positive" else 2 if rec == "negative" else 3

                    text = r.get("review_text", "")
                    created = r.get("created_time", "")

                    try:
                        date = datetime.fromisoformat(created.replace("+0000", "+00:00"))
                    except (ValueError, AttributeError):
                        date = datetime.now(timezone.utc)

                    reviews.append(Review(
                        id=f"facebook_{review_id}",
                        platform="facebook",
                        author=reviewer.get("name", "Facebook User"),
                        rating=int(rating),
                        text=text,
                        date=date,
                        platform_review_id=str(review_id),
                        metadata={"reviewer_id": reviewer.get("id", "")},
                    ))

                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # next URL includes params

        logger.info(f"Fetched {len(reviews)} Facebook reviews")
        return reviews

    async def post_reply(self, review_id: str, text: str) -> bool:
        """Reply to a Facebook review by commenting on the open graph story."""
        page_token = await self._get_page_token()
        url = f"{GRAPH_BASE}/{review_id}/comments"
        params = {
            "access_token": page_token,
            "message": text,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, params=params)
            resp.raise_for_status()

        logger.info(f"Replied to Facebook review {review_id}")
        return True
