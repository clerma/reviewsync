import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

# Minimum star rating to keep (filters out negative reviews)
MIN_RATING_THRESHOLD = 4


class Review(BaseModel):
    id: str
    platform: str  # google, facebook, yelp, website
    author: str
    rating: int = Field(ge=1, le=5)
    text: str = ""
    date: datetime
    reply: Optional[str] = None
    reply_date: Optional[datetime] = None
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    platform_review_id: str = ""
    event_type: str = "event"  # wedding, corporate, event, school, nonprofit, etc.
    booth: str = ""  # /portrait-booth, Social Booth, legacy, etc.
    metadata: dict = Field(default_factory=dict)


class ReviewStore:
    """JSON file-based review storage."""

    def __init__(self, filepath: str = "data/reviews.json"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if not os.path.exists(filepath):
            self._write([])

    def _read(self) -> list[dict]:
        with open(self.filepath, "r") as f:
            return json.load(f)

    def _write(self, data: list[dict]):
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_all(self) -> list[Review]:
        return [Review(**r) for r in self._read()]

    def get_by_id(self, review_id: str) -> Optional[Review]:
        for r in self._read():
            if r["id"] == review_id:
                return Review(**r)
        return None

    def get_by_platform(self, platform: str) -> list[Review]:
        return [Review(**r) for r in self._read() if r["platform"] == platform]

    def add(self, review: Review) -> bool:
        """Add a review. Returns False if it already exists."""
        data = self._read()
        if any(r["id"] == review.id for r in data):
            return False
        data.append(review.model_dump())
        self._write(data)
        return True

    def add_many(self, reviews: list[Review]) -> list[Review]:
        """Add multiple reviews, skipping duplicates. Returns newly added."""
        data = self._read()
        existing_ids = {r["id"] for r in data}
        new_reviews = [r for r in reviews if r.id not in existing_ids]
        if new_reviews:
            data.extend([r.model_dump() for r in new_reviews])
            self._write(data)
        return new_reviews

    def update_reply(self, review_id: str, reply: str) -> bool:
        data = self._read()
        for r in data:
            if r["id"] == review_id:
                r["reply"] = reply
                r["reply_date"] = datetime.now(timezone.utc).isoformat()
                self._write(data)
                return True
        return False

    def delete(self, review_id: str) -> bool:
        data = self._read()
        filtered = [r for r in data if r["id"] != review_id]
        if len(filtered) == len(data):
            return False
        self._write(filtered)
        return True

    def get_positive(self, min_rating: int = MIN_RATING_THRESHOLD) -> list[Review]:
        """Get only positive reviews (4+ stars by default)."""
        return [r for r in self.get_all() if r.rating >= min_rating]

    def stats(self) -> dict:
        reviews = self._read()
        if not reviews:
            return {"total": 0, "average_rating": 0, "by_platform": {}}

        by_platform = {}
        for r in reviews:
            p = r["platform"]
            if p not in by_platform:
                by_platform[p] = {"count": 0, "total_rating": 0}
            by_platform[p]["count"] += 1
            by_platform[p]["total_rating"] += r["rating"]

        for p in by_platform:
            by_platform[p]["average_rating"] = round(
                by_platform[p]["total_rating"] / by_platform[p]["count"], 2
            )
            del by_platform[p]["total_rating"]

        total = len(reviews)
        avg = round(sum(r["rating"] for r in reviews) / total, 2)
        return {"total": total, "average_rating": avg, "by_platform": by_platform}

    def export_to_testimonial_yml(self, output_path: str, min_rating: int = MIN_RATING_THRESHOLD):
        """Export positive reviews to Jekyll _data/testimonial.yml format.

        Output matches the existing ohhsnapbooth.com testimonial.yml structure:
          - date: 2025-02-04 00:00:00
            event-type: corporate
            name: John Doe
            testimony: >-
              Great service!
            booth: /portrait-booth
        """
        reviews = self.get_positive(min_rating)
        reviews.sort(key=lambda r: r.date, reverse=True)

        lines = []
        for r in reviews:
            date_str = r.date.strftime("%Y-%m-%d %H:%M:%S")
            event_type = r.event_type or "event"
            booth = r.booth or ""
            # Escape any YAML-problematic characters in text
            text = r.text.replace("\n", " ").strip()

            lines.append(f"- date: {date_str}")
            lines.append(f"  event-type: {event_type}")
            lines.append(f"  name: {r.author}")
            lines.append(f"  testimony: >-")
            # Wrap long text at ~76 chars with 4-space indent
            words = text.split()
            current_line = "    "
            for word in words:
                if len(current_line) + len(word) + 1 > 80:
                    lines.append(current_line.rstrip())
                    current_line = "    " + word
                else:
                    current_line += (" " if len(current_line.strip()) > 0 else "") + word
            if current_line.strip():
                lines.append(current_line.rstrip())
            lines.append(f"  booth: {booth}")
            lines.append(f"  platform: {r.platform}")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(lines) + "\n")


class BaseReviewProvider(ABC):
    """Abstract base class for review platform providers."""

    platform_name: str = ""
    supports_reply: bool = False

    @abstractmethod
    async def fetch_reviews(self) -> list[Review]:
        """Fetch reviews from the platform."""
        ...

    async def post_reply(self, review_id: str, text: str) -> bool:
        """Post a reply to a review. Override in subclasses that support it."""
        raise NotImplementedError(f"{self.platform_name} does not support replies via API")

    async def get_rating_summary(self) -> dict:
        """Get summary stats. Default implementation uses fetched reviews."""
        reviews = await self.fetch_reviews()
        if not reviews:
            return {"platform": self.platform_name, "count": 0, "average": 0}
        avg = round(sum(r.rating for r in reviews) / len(reviews), 2)
        return {"platform": self.platform_name, "count": len(reviews), "average": avg}


# Global store instance
store = ReviewStore()
