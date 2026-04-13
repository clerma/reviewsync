import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from providers.base import Review, ReviewStore


@pytest.fixture
def temp_store():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([], f)
        path = f.name
    store = ReviewStore(filepath=path)
    yield store
    os.unlink(path)


def make_review(platform="google", rating=5, review_id=None):
    rid = review_id or f"{platform}_test123"
    return Review(
        id=rid,
        platform=platform,
        author="Test User",
        rating=rating,
        text="Great experience!",
        date=datetime.now(timezone.utc),
        platform_review_id="test123",
    )


class TestReviewStore:
    def test_add_review(self, temp_store):
        review = make_review()
        assert temp_store.add(review) is True
        assert len(temp_store.get_all()) == 1

    def test_no_duplicates(self, temp_store):
        review = make_review()
        temp_store.add(review)
        assert temp_store.add(review) is False
        assert len(temp_store.get_all()) == 1

    def test_add_many(self, temp_store):
        reviews = [
            make_review(platform="google", review_id="google_1"),
            make_review(platform="facebook", review_id="facebook_1"),
            make_review(platform="yelp", review_id="yelp_1"),
        ]
        new = temp_store.add_many(reviews)
        assert len(new) == 3
        assert len(temp_store.get_all()) == 3

    def test_add_many_skips_duplicates(self, temp_store):
        r1 = make_review(review_id="google_1")
        temp_store.add(r1)

        reviews = [
            make_review(review_id="google_1"),
            make_review(review_id="google_2"),
        ]
        new = temp_store.add_many(reviews)
        assert len(new) == 1
        assert len(temp_store.get_all()) == 2

    def test_get_by_id(self, temp_store):
        review = make_review()
        temp_store.add(review)
        found = temp_store.get_by_id(review.id)
        assert found is not None
        assert found.author == "Test User"

    def test_get_by_id_not_found(self, temp_store):
        assert temp_store.get_by_id("nonexistent") is None

    def test_get_by_platform(self, temp_store):
        temp_store.add(make_review(platform="google", review_id="g1"))
        temp_store.add(make_review(platform="facebook", review_id="f1"))
        temp_store.add(make_review(platform="google", review_id="g2"))

        google = temp_store.get_by_platform("google")
        assert len(google) == 2

    def test_update_reply(self, temp_store):
        review = make_review()
        temp_store.add(review)
        assert temp_store.update_reply(review.id, "Thank you!") is True

        updated = temp_store.get_by_id(review.id)
        assert updated.reply == "Thank you!"

    def test_delete(self, temp_store):
        review = make_review()
        temp_store.add(review)
        assert temp_store.delete(review.id) is True
        assert len(temp_store.get_all()) == 0

    def test_delete_not_found(self, temp_store):
        assert temp_store.delete("nonexistent") is False

    def test_stats(self, temp_store):
        temp_store.add(make_review(platform="google", rating=5, review_id="g1"))
        temp_store.add(make_review(platform="google", rating=3, review_id="g2"))
        temp_store.add(make_review(platform="yelp", rating=4, review_id="y1"))

        stats = temp_store.stats()
        assert stats["total"] == 3
        assert stats["average_rating"] == 4.0
        assert stats["by_platform"]["google"]["count"] == 2
        assert stats["by_platform"]["google"]["average_rating"] == 4.0
        assert stats["by_platform"]["yelp"]["count"] == 1

    def test_stats_empty(self, temp_store):
        stats = temp_store.stats()
        assert stats["total"] == 0
        assert stats["average_rating"] == 0


class TestReviewModel:
    def test_valid_review(self):
        review = make_review()
        assert review.platform == "google"
        assert review.rating == 5

    def test_rating_bounds(self):
        with pytest.raises(Exception):
            make_review(rating=0)
        with pytest.raises(Exception):
            make_review(rating=6)
