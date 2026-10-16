from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product, SavedProduct
from journal.models import DecisionEntry

User = get_user_model()


class DecisionJournalTests(TestCase):
    def setUp(self) -> None:
        self.user_a = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Password123!",
        )
        self.user_b = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="Password123!",
        )
        self.laptop_cat = Category.objects.create(name="Laptops", slug="laptops")
        self.phone_cat = Category.objects.create(name="Phones", slug="phones")

        self.gpu_crit = Criteria.objects.create(
            category=self.laptop_cat, name="GPU Performance"
        )

        self.laptop = Product.objects.create(
            category=self.laptop_cat,
            brand="Lenovo",
            name="LOQ 15",
            slug="lenovo-loq-15",
        )
        self.phone = Product.objects.create(
            category=self.phone_cat,
            brand="Samsung",
            name="Galaxy S24",
            slug="galaxy-s24",
        )

    def test_create_valid_decision_entry_with_weights_snapshot(self) -> None:
        entry = DecisionEntry.objects.create(
            user=self.user_a,
            category=self.laptop_cat,
            chosen_product=self.laptop,
            weights_snapshot={"Battery": 5.0, "GPU Performance": 8.0},
            rationale="Best thermal performance in this price bracket.",
        )
        self.assertIsNone(entry.satisfaction_rating)
        self.assertEqual(entry.weights_snapshot["GPU Performance"], 8.0)

    def test_mismatched_category_and_product_fails_clean(self) -> None:
        invalid_entry = DecisionEntry(
            user=self.user_a,
            category=self.laptop_cat,
            chosen_product=self.phone,
            rationale="Invalid cross-category selection.",
        )
        with self.assertRaises(ValidationError):
            invalid_entry.full_clean()

    def test_satisfaction_rating_check_constraint(self) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DecisionEntry.objects.create(
                    user=self.user_a,
                    category=self.laptop_cat,
                    chosen_product=self.laptop,
                    rationale="Testing invalid rating constraint.",
                    satisfaction_rating=12,
                )

    def test_journal_list_view_isolates_user_entries(self) -> None:
        DecisionEntry.objects.create(
            user=self.user_a,
            category=self.laptop_cat,
            chosen_product=self.laptop,
            rationale="Alice's laptop choice.",
        )
        DecisionEntry.objects.create(
            user=self.user_b,
            category=self.phone_cat,
            chosen_product=self.phone,
            rationale="Bob's phone choice.",
        )

        self.client.force_login(self.user_a)
        response = self.client.get(reverse("journal_list"))
        self.assertEqual(response.status_code, 200)
        entries = list(response.context["entries"])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].user, self.user_a)

    def test_record_decision_post_view_creates_entry_with_named_weights(self) -> None:
        self.client.force_login(self.user_a)
        url = reverse("record_decision", kwargs={"product_slug": self.laptop.slug})
        response = self.client.post(
            url,
            {
                "rationale": "Selected after comparing weighted GPU scores.",
                "expected_outcome": "Fast local AI training.",
                "expected_rating": "8",
                "satisfaction_rating": "9",
                f"weight_{self.gpu_crit.id}": "8.0",
            },
        )
        self.assertRedirects(response, reverse("journal_list"))
        entry = DecisionEntry.objects.get(user=self.user_a)
        self.assertEqual(entry.weights_snapshot["GPU Performance"], 8.0)
        self.assertEqual(entry.expectation_gap, 1)

    def test_record_decision_invalid_satisfaction_15_returns_form_errors_not_500(self) -> None:
        self.client.force_login(self.user_a)
        url = reverse("record_decision", kwargs={"product_slug": self.laptop.slug})
        response = self.client.post(
            url,
            {
                "rationale": "Testing out-of-range satisfaction score.",
                "satisfaction_rating": "15",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(DecisionEntry.objects.count(), 0)

    def test_update_post_purchase_experience_view(self) -> None:
        """User can update actual_experience and satisfaction_rating months after purchase."""
        entry = DecisionEntry.objects.create(
            user=self.user_a,
            category=self.laptop_cat,
            chosen_product=self.laptop,
            rationale="Initial purchase rationale.",
            expected_rating=7,
        )
        self.client.force_login(self.user_a)
        url = reverse("update_decision", kwargs={"entry_id": entry.id})
        response = self.client.post(
            url,
            {
                "rationale": "Initial purchase rationale.",
                "expected_rating": "7",
                "actual_experience": "Exceeded expectations after 3 months!",
                "satisfaction_rating": "9",
            },
        )
        self.assertRedirects(response, reverse("journal_list"))
        entry.refresh_from_db()
        self.assertEqual(entry.satisfaction_rating, 9)
        self.assertEqual(entry.expectation_gap, 2)

    def test_dashboard_view_aggregates_expected_vs_actual_and_saved_products(self) -> None:
        """Dashboard view computes avg_expected, avg_actual, and lists saved products."""
        SavedProduct.objects.create(user=self.user_a, product=self.laptop)
        DecisionEntry.objects.create(
            user=self.user_a,
            category=self.laptop_cat,
            chosen_product=self.laptop,
            rationale="Dashboard test entry.",
            expected_rating=8,
            satisfaction_rating=10,
        )
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["avg_expected"], 8.0)
        self.assertEqual(response.context["avg_actual"], 10.0)
        self.assertEqual(response.context["saved_products"].count(), 1)
