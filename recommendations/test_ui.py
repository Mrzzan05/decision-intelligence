import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Category, Criteria, Product
from recommendations.services import (
    build_platform_analytics,
    rank_products_for_category,
    script_safe_json,
)
from reviews.models import Review, ReviewScore

User = get_user_model()


class ScriptSafeJsonTests(TestCase):
    def test_closing_script_tag_cannot_break_out(self) -> None:
        payload = {"label": "</script><script>alert(1)</script>", "amp": "a&b"}
        encoded = script_safe_json(payload)
        self.assertNotIn("<", encoded)
        self.assertNotIn(">", encoded)
        self.assertNotIn("&", encoded)
        self.assertEqual(json.loads(encoded), payload)  # still valid, lossless JSON


class AnalyticsAndSummaryTests(TestCase):
    def setUp(self) -> None:
        self.cat = Category.objects.create(name="Laptops", slug="laptops")
        self.crit = Criteria.objects.create(category=self.cat, name="Battery")
        self.p1 = Product.objects.create(category=self.cat, brand="A", name="One", slug="a-one", price=900)
        self.p2 = Product.objects.create(category=self.cat, brand="B", name="Two", slug="b-two", price=800)
        Product.objects.create(category=self.cat, brand="C", name="Three", slug="c-three", price=700)
        for i in range(3):
            user = User.objects.create_user(username=f"u{i}", email=f"u{i}@example.com", password="Pass12345!x")
            for product, score in ((self.p1, 9), (self.p2, 6)):
                if product is self.p2 and i > 0:
                    continue
                review = Review.objects.create(user=user, product=product, overall_rating=score)
                ReviewScore.objects.create(review=review, criteria=self.crit, score=score)

    def test_platform_analytics_orders_and_skips_unreviewed(self) -> None:
        data = build_platform_analytics()
        self.assertEqual([p.slug for p in data["most_reviewed"]], ["a-one", "b-two"])
        self.assertEqual(data["most_reviewed"][0].popularity_pct, 100)
        self.assertEqual(data["top_rated"][0].slug, "a-one")
        self.assertEqual(data["by_category"][0].review_total, 4)
        self.assertEqual(sum(m["total"] for m in data["monthly"]), 4)

    def test_platform_analytics_uses_constant_queries(self) -> None:
        with self.assertNumQueries(4):
            build_platform_analytics()

    def test_summary_does_not_claim_reviews_are_verified(self) -> None:
        ranked = rank_products_for_category(self.cat)
        for product in ranked:
            self.assertNotIn("verified", product.smart_summary["verdict"].lower())
            self.assertNotIn("verified", product.smart_summary["basis_text"].lower())
