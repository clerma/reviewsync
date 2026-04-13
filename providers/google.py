import logging
from datetime import datetime, timezone

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

from config import settings
from providers.base import BaseReviewProvider, Review

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/business.manage"]


class GoogleReviewProvider(BaseReviewProvider):
    platform_name = "google"
    supports_reply = True

    def __init__(self):
        self.account_id = settings.google_account_id
        self.location_id = settings.google_location_id
        self._credentials = None

    def _get_access_token(self) -> str:
        if not settings.google_service_account_json:
            raise ValueError("Google service account JSON path not configured")
        if self._credentials is None or not self._credentials.valid:
            self._credentials = service_account.Credentials.from_service_account_file(
                settings.google_service_account_json, scopes=SCOPES
            )
            self._credentials.refresh(GoogleAuthRequest())
        return self._credentials.token

    async def fetch_reviews(self) -> list[Review]:
        if not self.account_id or not self.location_id:
            logger.warning("Google provider not configured, skipping")
            return []

        token = self._get_access_token()
        url = (
            f"https://mybusiness.googleapis.com/v4/"
            f"{self.account_id}/{self.location_id}/reviews"
        )
        headers = {"Authorization": f"Bearer {token}"}

        reviews = []
        next_page = None

        async with httpx.AsyncClient() as client:
            while True:
                params = {"pageSize": 50}
                if next_page:
                    params["pageToken"] = next_page

                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                for r in data.get("reviews", []):
                    review_id = r["reviewId"]
                    reviewer = r.get("reviewer", {})
                    star_rating = r.get("starRating", "FIVE")
                    rating_map = {
                        "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
                    }
                    rating = rating_map.get(star_rating, 5)
                    comment = r.get("comment", "")
                    create_time = r.get("createTime", "")

                    reply_text = None
                    reply_date = None
                    if "reviewReply" in r:
                        reply_text = r["reviewReply"].get("comment", "")
                        reply_date = r["reviewReply"].get("updateTime")

                    try:
                        date = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        date = datetime.now(timezone.utc)

                    reviews.append(Review(
                        id=f"google_{review_id}",
                        platform="google",
                        author=reviewer.get("displayName", "Anonymous"),
                        rating=rating,
                        text=comment,
                        date=date,
                        reply=reply_text,
                        reply_date=datetime.fromisoformat(reply_date.replace("Z", "+00:00")) if reply_date else None,
                        platform_review_id=review_id,
                        metadata={"profile_photo": reviewer.get("profilePhotoUrl", "")},
                    ))

                next_page = data.get("nextPageToken")
                if not next_page:
                    break

        logger.info(f"Fetched {len(reviews)} Google reviews")
        return reviews

    async def post_reply(self, review_id: str, text: str) -> bool:
        token = self._get_access_token()
        url = (
            f"https://mybusiness.googleapis.com/v4/"
            f"{self.account_id}/{self.location_id}/reviews/{review_id}/reply"
        )
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            resp = await client.put(url, headers=headers, json={"comment": text})
            resp.raise_for_status()

        logger.info(f"Replied to Google review {review_id}")
        return True
