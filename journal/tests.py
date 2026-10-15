from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product
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
        """Submitting the decision form saves human-readable criteria names in weights_snapshot."""
        self.client.force_login(self.user_a)
        url = reverse("record_decision", kwargs={"product_slug": self.laptop.slug})
        response = self.client.post(
            url,
            {
                "rationale": "Selected after comparing weighted GPU scores.",
                "satisfaction_rating": "9",
                f"weight_{self.gpu_crit.id}": "8.0",
            },
        )
        self.assertRedirects(response, reverse("journal_list"))
        entry = DecisionEntry.objects.get(user=self.user_a)
        self.assertEqual(entry.weights_snapshot["GPU Performance"], 8.0)

    def test_record_decision_invalid_satisfaction_15_returns_form_errors_not_500(self) -> None:
        """Entering satisfaction_rating=15 must return HTTP 200 with form errors instead of crashing."""
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