import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from providers.base import store

router = APIRouter(tags=["share"])


@router.get("/share/{review_id}")
async def share_review(review_id: str):
    review = store.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    stars = "\u2605" * review.rating + "\u2606" * (5 - review.rating)
    formatted = (
        f"{stars}\n"
        f'"{review.text}"\n'
        f"- {review.author}, via {review.platform.title()}"
    )

    return {
        "review": review.model_dump(),
        "formatted_text": formatted,
        "share_urls": {
            "twitter": f"https://twitter.com/intent/tweet?text={formatted[:200]}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php",
        },
    }


@router.get("/share/{review_id}/card", response_class=HTMLResponse)
async def share_card(review_id: str):
    review = store.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    stars = "\u2605" * review.rating + "\u2606" * (5 - review.rating)
    platform_colors = {
        "google": "#4285f4",
        "facebook": "#1877f2",
        "yelp": "#d32323",
        "website": "#28a745",
    }
    color = platform_colors.get(review.platform, "#333")
    text = review.text[:300] + "..." if len(review.text) > 300 else review.text

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .card {{ width: 600px; padding: 40px; background: linear-gradient(135deg, #ffffff, #f8f9fa); border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); }}
    .stars {{ font-size: 2em; color: #ffc107; margin-bottom: 16px; }}
    .text {{ font-size: 1.2em; line-height: 1.6; color: #333; margin-bottom: 20px; font-style: italic; }}
    .author {{ font-weight: 600; font-size: 1.1em; color: #555; }}
    .platform {{ display: inline-block; background: {color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; margin-left: 8px; }}
    .date {{ font-size: 0.85em; color: #999; margin-top: 8px; }}
</style>
</head>
<body>
    <div class="card">
        <div class="stars">{stars}</div>
        <div class="text">"{text}"</div>
        <div>
            <span class="author">{review.author}</span>
            <span class="platform">{review.platform.title()}</span>
        </div>
        <div class="date">{review.date.strftime('%B %d, %Y')}</div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html)


@router.get("/share/batch")
async def batch_export(
    format: str = Query("json", description="Export format: json or csv"),
    platform: Optional[str] = Query(None),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
):
    reviews = store.get_all()

    if platform:
        reviews = [r for r in reviews if r.platform == platform]
    if min_rating is not None:
        reviews = [r for r in reviews if r.rating >= min_rating]

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "platform", "author", "rating", "text", "date", "reply"])
        for r in reviews:
            writer.writerow([r.id, r.platform, r.author, r.rating, r.text, r.date.isoformat(), r.reply or ""])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=reviews.csv"},
        )

    return {"total": len(reviews), "reviews": [r.model_dump() for r in reviews]}
