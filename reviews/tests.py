from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product
from reviews.models import Review, ReviewScore

User = get_user_model()


class ReviewModelAndAggregationTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="reviewer1",
            email="reviewer1@example.com",
            password="StrongPassword123!",
        )
        self.laptop_cat = Category.objects.create(name="Laptops", slug="laptops")
        self.phone_cat = Category.objects.create(name="Phones", slug="phones")

        self.battery_criteria = Criteria.objects.create(
            category=self.laptop_cat, name="Battery"
        )
        self.screen_criteria = Criteria.objects.create(
            category=self.laptop_cat, name="Screen"
        )
        self.camera_criteria = Criteria.objects.create(
            category=self.phone_cat, name="Camera"
        )

        self.product = Product.objects.create(
            category=self.laptop_cat,
            brand="Lenovo",
            name="LOQ 15",
            slug="lenovo-loq-15",
            price=950,
        )

    def test_unique_review_per_user_and_product(self) -> None:
        Review.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=self.user, product=self.product)

    def test_score_range_check_constraint(self) -> None:
        review = Review.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReviewScore.objects.create(
                    review=review,
                    criteria=self.battery_criteria,
                    score=15,
                )

    def test_cross_category_criteria_validation(self) -> None:
        review = Review.objects.create(user=self.user, product=self.product)
        invalid_score = ReviewScore(
            review=review,
            criteria=self.camera_criteria,
            score=8,
        )
        with self.assertRaises(ValidationError):
            invalid_score.full_clean()

    def test_product_with_average_scores_annotation(self) -> None:
        review = Review.objects.create(user=self.user, product=self.product)
        ReviewScore.objects.create(
            review=review, criteria=self.battery_criteria, score=8
        )
        ReviewScore.objects.create(
            review=review, criteria=self.screen_criteria, score=10
        )

        annotated_product = (
            Product.objects.with_average_scores().get(pk=self.product.pk)
        )
        self.assertAlmostEqual(annotated_product.average_score, 9.0)
        self.assertEqual(annotated_product.review_count, 1)

    def test_user_can_submit_and_delete_structured_review_via_views(self) -> None:
        """Verify end-to-end user review submission with pros/cons and per-criteria scores."""
        self.client.force_login(self.user)
        write_url = reverse("reviews:write_review", kwargs={"product_slug": self.product.slug})
        response = self.client.post(
            write_url,
            {
                "overall_rating": "9",
                "pros": "Great GPU",
                "cons": "Heavy",
                "comment": "Solid laptop for engineering.",
                f"criteria_{self.battery_criteria.id}": "7",
                f"criteria_{self.screen_criteria.id}": "9",
            },
        )
        self.assertRedirects(
            response,
            reverse("catalog:product_detail", kwargs={"product_slug": self.product.slug}),
        )
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(ReviewScore.objects.count(), 2)

        # Now delete the review
        delete_url = reverse("reviews:delete_review", kwargs={"product_slug": self.product.slug})
        self.client.post(delete_url)
        self.assertEqual(Review.objects.count(), 0)
