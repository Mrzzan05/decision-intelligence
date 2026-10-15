from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product
from recommendations.services import rank_products_for_category
from reviews.models import Review, ReviewScore

User = get_user_model()


class RecommendationEngineTests(TestCase):
    def setUp(self) -> None:
        self.user_1 = User.objects.create_user(
            username="analyst1", email="a1@example.com", password="Password123!"
        )
        self.user_2 = User.objects.create_user(
            username="analyst2", email="a2@example.com", password="Password123!"
        )
        self.category = Category.objects.create(name="Laptops", slug="laptops")

        self.battery_criteria = Criteria.objects.create(
            category=self.category, name="Battery Life"
        )
        self.gpu_criteria = Criteria.objects.create(
            category=self.category, name="GPU Performance"
        )
        # Sub-criterion under GPU Performance
        self.raytracing_subcriteria = Criteria.objects.create(
            category=self.category,
            parent=self.gpu_criteria,
            name="Ray Tracing",
        )

        # Product 1: Great battery (10), weak GPU (4)
        self.ultrabook = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="ThinkPad X1",
            slug="thinkpad-x1",
        )
        r1 = Review.objects.create(user=self.user_1, product=self.ultrabook)
        ReviewScore.objects.create(review=r1, criteria=self.battery_criteria, score=10)
        ReviewScore.objects.create(review=r1, criteria=self.gpu_criteria, score=4)

        # Product 2: Weak battery (4), great GPU (9)
        self.gaming_laptop = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="LOQ Gaming",
            slug="loq-gaming",
        )
        r2 = Review.objects.create(user=self.user_1, product=self.gaming_laptop)
        ReviewScore.objects.create(review=r2, criteria=self.battery_criteria, score=4)
        ReviewScore.objects.create(review=r2, criteria=self.gpu_criteria, score=9)
        # Add sub-criterion score to verify it does NOT double-count GPU in weighted_score
        ReviewScore.objects.create(review=r2, criteria=self.raytracing_subcriteria, score=2)

    def test_ranking_shifts_and_subcriteria_are_not_double_counted(self) -> None:
        """
        Verify changing weights flips #1 product AND sub-criteria do not distort top-level weighted average.
        """
        gamer_ranking = rank_products_for_category(
            category=self.category,
            weights={self.battery_criteria.id: 1.0, self.gpu_criteria.id: 5.0},
        )
        self.assertEqual(gamer_ranking[0], self.gaming_laptop)
        # (4*1 + 9*5) / 6 = 49 / 6 = 8.17 (Ray Tracing sub-criterion score=2 is NOT double-counted!)
        self.assertAlmostEqual(gamer_ranking[0].weighted_score, 8.17)

    def test_unreviewed_product_shows_none_match_not_zero_percent(self) -> None:
        """A product with 0 reviews must have has_sufficient_data=False and match_percentage=None."""
        unreviewed = Product.objects.create(
            category=self.category,
            brand="Dell",
            name="XPS Unreviewed",
            slug="xps-unreviewed",
        )
        ranked = rank_products_for_category(self.category)
        unreviewed_entry = next(p for p in ranked if p.id == unreviewed.id)
        self.assertFalse(unreviewed_entry.has_sufficient_data)
        self.assertIsNone(unreviewed_entry.match_percentage)
        self.assertEqual(ranked[-1], unreviewed)

    def test_dealbreaker_penalty_reduces_match_percentage(self) -> None:
        """When a critical criterion (weight >= 8) scores < 6, dealbreaker penalty triggers."""
        ranked = rank_products_for_category(
            self.category,
            weights={self.battery_criteria.id: 9.0, self.gpu_criteria.id: 9.0},
        )
        # Both laptops have a score of 4 (< 6.0) on one of the weight=9 criteria
        for prod in ranked:
            self.assertEqual(len(prod.dealbreakers), 1)
            raw_pct = int(round((prod.weighted_score / 10.0) * 100))
            self.assertLess(prod.match_percentage, raw_pct)

    def test_smart_summary_detects_mixed_opinions_via_stddev(self) -> None:
        """High variance across reviewers (e.g., 10 vs 2) must produce a 'mixed' consensus item."""
        r_second = Review.objects.create(user=self.user_2, product=self.gaming_laptop)
        ReviewScore.objects.create(
            review=r_second, criteria=self.raytracing_subcriteria, score=10
        )
        ranked = rank_products_for_category(self.category)
        gaming = next(p for p in ranked if p.id == self.gaming_laptop.id)
        mixed_text = " ".join(gaming.smart_summary["mixed"])
        self.assertIn("Opinions are mixed on Ray Tracing", mixed_text)

    def test_negative_weight_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            rank_products_for_category(
                category=self.category,
                weights={self.battery_criteria.id: -2.0},
            )

    def test_service_executes_in_constant_three_queries(self) -> None:
        with self.assertNumQueries(3):
            rank_products_for_category(
                category=self.category,
                weights={self.battery_criteria.id: 3.0, self.gpu_criteria.id: 2.0},
            )

    def test_recommendations_view_renders_ranked_products(self) -> None:
        url = reverse(
            "recommendations:category_recommendations",
            kwargs={"category_slug": "laptops"},
        )
        response = self.client.get(
            url,
            {
                f"weight_{self.battery_criteria.id}": "1",
                f"weight_{self.gpu_criteria.id}": "5",
            },
        )
        self.assertEqual(response.status_code, 200)
        products_in_context = response.context["products"]
        self.assertEqual(products_in_context[0], self.gaming_laptop)
