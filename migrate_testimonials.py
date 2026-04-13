"""
Migrate existing testimonial.yml entries into the review plugin's JSON store.

Imports your current ohhsnapbooth.com testimonials so they're preserved
alongside new reviews pulled from Google, Facebook, and Yelp.

Usage:
    python migrate_testimonials.py /Volumes/floppy/GitHub/ohhsnap/_data/testimonial.yml
"""

import sys
import yaml
from datetime import datetime, timezone

from providers.base import Review, store


def migrate(yml_path: str):
    with open(yml_path, "r") as f:
        testimonials = yaml.safe_load(f)

    if not testimonials:
        print("No testimonials found.")
        return

    reviews = []
    for i, t in enumerate(testimonials):
        name = t.get("name", "Anonymous")
        text = t.get("testimony", "").strip()
        event_type = t.get("event-type", "event")
        booth = t.get("booth", "") or ""
        date_val = t.get("date")

        if isinstance(date_val, datetime):
            date = date_val.replace(tzinfo=timezone.utc)
        elif isinstance(date_val, str):
            try:
                date = datetime.fromisoformat(date_val).replace(tzinfo=timezone.utc)
            except ValueError:
                date = datetime.now(timezone.utc)
        else:
            date = datetime.now(timezone.utc)

        # Create a stable ID from name + date to avoid duplicates on re-import
        stable_id = f"website_{name.lower().replace(' ', '_')}_{date.strftime('%Y%m%d')}"

        reviews.append(Review(
            id=stable_id,
            platform="website",
            author=name,
            rating=5,  # existing testimonials are all positive / curated
            text=text,
            date=date,
            event_type=event_type,
            booth=booth,
            platform_review_id=f"legacy_{i}",
        ))

    new = store.add_many(reviews)
    print(f"Imported {len(new)} new testimonials ({len(reviews) - len(new)} already existed)")
    print(f"Total reviews in store: {len(store.get_all())}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_testimonials.py <path-to-testimonial.yml>")
        sys.exit(1)
    migrate(sys.argv[1])
