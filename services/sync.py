import logging
from datetime import datetime, timezone

from config import settings
from providers.base import MIN_RATING_THRESHOLD, Review, store
from providers.google import GoogleReviewProvider
from providers.facebook import FacebookReviewProvider
from providers.yelp import YelpReviewProvider
from services.notifier import notify_new_reviews
from services.responder import auto_respond

logger = logging.getLogger(__name__)


async def sync_all_reviews() -> dict:
    """Pull reviews from all platforms, deduplicate, store, notify, and export YAML."""
    providers = [
        GoogleReviewProvider(),
        FacebookReviewProvider(),
        YelpReviewProvider(),
    ]

    all_new: list[Review] = []
    errors: dict[str, str] = {}

    for provider in providers:
        try:
            reviews = await provider.fetch_reviews()
            new = store.add_many(reviews)
            all_new.extend(new)
            logger.info(f"{provider.platform_name}: {len(new)} new / {len(reviews)} total")
        except Exception as e:
            logger.error(f"Error syncing {provider.platform_name}: {e}")
            errors[provider.platform_name] = str(e)

    # Filter out negative reviews and notify only about positive ones
    positive_new = [r for r in all_new if r.rating >= MIN_RATING_THRESHOLD]
    negative_new = [r for r in all_new if r.rating < MIN_RATING_THRESHOLD]

    if negative_new:
        logger.info(f"Filtered out {len(negative_new)} reviews below {MIN_RATING_THRESHOLD} stars")

    if positive_new:
        await notify_new_reviews(positive_new)
        await auto_respond(positive_new)

    # Export positive reviews and push to GitHub
    github_result = None
    if all_new:
        try:
            # Generate the YAML content
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tmp:
                tmp_path = tmp.name
            store.export_to_testimonial_yml(tmp_path)
            with open(tmp_path, "r") as f:
                yml_content = f.read()
            import os
            os.unlink(tmp_path)

            # Also write locally if path is set
            if settings.testimonial_yml_path:
                store.export_to_testimonial_yml(settings.testimonial_yml_path)
                logger.info(f"Exported testimonials to {settings.testimonial_yml_path}")

            # Push to GitHub → triggers CloudCannon rebuild
            if settings.github_token and settings.github_repo:
                from services.github import push_testimonial_yml
                github_result = await push_testimonial_yml(yml_content)
                logger.info(f"Pushed to GitHub: {github_result['commit'][:7]}")

        except Exception as e:
            logger.error(f"Failed to export/push testimonials: {e}")
            errors["testimonial_export"] = str(e)

    return {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "new_reviews": len(all_new),
        "positive_reviews": len(positive_new),
        "filtered_negative": len(negative_new),
        "github_push": github_result,
        "errors": errors,
        "platforms": {
            "google": len([r for r in all_new if r.platform == "google"]),
            "facebook": len([r for r in all_new if r.platform == "facebook"]),
            "yelp": len([r for r in all_new if r.platform == "yelp"]),
        },
    }
