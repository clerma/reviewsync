from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from config import settings
from providers.base import MIN_RATING_THRESHOLD, store, Review
from providers.website import WebsiteReviewProvider
from providers.google import GoogleReviewProvider
from providers.facebook import FacebookReviewProvider
from services.sync import sync_all_reviews

router = APIRouter(tags=["reviews"])


class ReviewSubmission(BaseModel):
    author: str = Field(min_length=1, max_length=100)
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=2000)
    event_type: str = Field(default="event", max_length=50)
    booth: str = Field(default="", max_length=100)


class ReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


@router.get("/reviews")
async def list_reviews(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    sort: str = Query("newest", description="Sort: newest, oldest, highest, lowest"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    reviews = store.get_all()

    if platform:
        reviews = [r for r in reviews if r.platform == platform]
    if min_rating is not None:
        reviews = [r for r in reviews if r.rating >= min_rating]
    if max_rating is not None:
        reviews = [r for r in reviews if r.rating <= max_rating]

    sort_key = {
        "newest": lambda r: r.date,
        "oldest": lambda r: r.date,
        "highest": lambda r: r.rating,
        "lowest": lambda r: r.rating,
    }.get(sort, lambda r: r.date)

    reverse = sort in ("newest", "highest")
    reviews.sort(key=sort_key, reverse=reverse)

    total = len(reviews)
    reviews = reviews[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "reviews": [r.model_dump() for r in reviews],
    }


@router.get("/reviews/stats")
async def review_stats():
    return store.stats()


@router.get("/reviews/{review_id}")
async def get_review(review_id: str):
    review = store.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review.model_dump()


@router.post("/reviews", status_code=201)
async def submit_review(submission: ReviewSubmission):
    provider = WebsiteReviewProvider()
    review = await provider.submit_review(
        author=submission.author,
        rating=submission.rating,
        text=submission.text,
    )
    return review.model_dump()


@router.post("/reviews/{review_id}/reply")
async def reply_to_review(review_id: str, reply: ReplyRequest):
    review = store.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    providers_with_reply = {
        "google": GoogleReviewProvider,
        "facebook": FacebookReviewProvider,
        "website": WebsiteReviewProvider,
    }

    if review.platform not in providers_with_reply:
        raise HTTPException(
            status_code=400,
            detail=f"Replies not supported for {review.platform}",
        )

    provider = providers_with_reply[review.platform]()
    try:
        await provider.post_reply(review.platform_review_id, reply.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to post reply: {e}")

    store.update_reply(review_id, reply.text)
    return {"status": "replied", "review_id": review_id}


@router.post("/sync")
async def trigger_sync():
    result = await sync_all_reviews()
    return result


@router.post("/export-testimonials")
async def export_testimonials():
    """Export positive reviews (4+ stars) to Jekyll testimonial.yml format."""
    if not settings.testimonial_yml_path:
        raise HTTPException(
            status_code=400,
            detail="TESTIMONIAL_YML_PATH not configured in .env",
        )

    try:
        store.export_to_testimonial_yml(settings.testimonial_yml_path)
        positive_count = len(store.get_positive())
        total_count = len(store.get_all())
        return {
            "status": "exported",
            "path": settings.testimonial_yml_path,
            "positive_reviews": positive_count,
            "total_reviews": total_count,
            "filtered_out": total_count - positive_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
