from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product
from recommendations.services import rank_products_for_category
from reviews.models import Review, ReviewScore

User = get_user_model()


class RecommendationEngineTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="analyst",
            email="analyst@example.com",
            password="StrongPassword123!",
        )
        self.category = Category.objects.create(name="Laptops", slug="laptops")

        # Two competing decision criteria
        self.battery_criteria = Criteria.objects.create(
            category=self.category, name="Battery Life"
        )
        self.gpu_criteria = Criteria.objects.create(
            category=self.category, name="GPU Performance"
        )

        # Product 1: Great battery (10), weak GPU (4) -> Unweighted Avg = 7.0
        self.ultrabook = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="ThinkPad X1",
            slug="thinkpad-x1",
        )
        r1 = Review.objects.create(user=self.user, product=self.ultrabook)
        ReviewScore.objects.create(
            review=r1, criteria=self.battery_criteria, score=10
        )
        ReviewScore.objects.create(review=r1, criteria=self.gpu_criteria, score=4)

        # Product 2: Weak battery (4), great GPU (9) -> Unweighted Avg = 6.5
        self.gaming_laptop = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="LOQ Gaming",
            slug="loq-gaming",
        )
        r2 = Review.objects.create(user=self.user, product=self.gaming_laptop)
        ReviewScore.objects.create(
            review=r2, criteria=self.battery_criteria, score=4
        )
        ReviewScore.objects.create(review=r2, criteria=self.gpu_criteria, score=9)

    def test_ranking_shifts_based_on_user_criteria_weights(self) -> None:
        """
        Verify that changing criteria weights flips the recommended #1 product.
        """
        # Scenario A: Traveler prioritizes Battery (weight=5) over GPU (weight=1)
        traveler_ranking = rank_products_for_category(
            category=self.category,
            weights={self.battery_criteria.id: 5.0, self.gpu_criteria.id: 1.0},
        )
        self.assertEqual(traveler_ranking[0], self.ultrabook)
        # (10*5 + 4*1) / 6 = 54 / 6 = 9.0
        self.assertAlmostEqual(traveler_ranking[0].weighted_score, 9.0)

        # Scenario B: Gamer prioritizes GPU (weight=5) over Battery (weight=1)
        gamer_ranking = rank_products_for_category(
            category=self.category,
            weights={self.battery_criteria.id: 1.0, self.gpu_criteria.id: 5.0},
        )
        self.assertEqual(gamer_ranking[0], self.gaming_laptop)
        # (4*1 + 9*5) / 6 = 49 / 6 = 8.17
        self.assertAlmostEqual(gamer_ranking[0].weighted_score, 8.17)

    def test_negative_weight_raises_value_error(self) -> None:
        """Service layer must reject negative weights."""
        with self.assertRaises(ValueError):
            rank_products_for_category(
                category=self.category,
                weights={self.battery_criteria.id: -2.0},
            )

    def test_service_executes_in_constant_three_queries(self) -> None:
        """Ensure zero N+1 query issues inside the recommendation service."""
        with self.assertNumQueries(3):
            rank_products_for_category(
                category=self.category,
                weights={self.battery_criteria.id: 3.0, self.gpu_criteria.id: 2.0},
            )

    def test_recommendations_view_renders_ranked_products(self) -> None:
        """Verify thin view parses query params and returns HTTP 200 with ranked context."""
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