from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product, SavedProduct
from reviews.models import Review

User = get_user_model()


class CatalogModelAndViewTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="mehrsan",
            email="private_email@example.com",
            password="StrongPass123!",
        )
        self.category = Category.objects.create(
            name="Laptops",
            slug="laptops",
            spec_schema=[
                {"key": "ram_gb", "label": "RAM", "unit": "GB", "higher_is_better": True, "group": "Memory"},
                {"key": "weight_kg", "label": "Weight", "unit": "kg", "higher_is_better": False, "group": "Chassis"},
            ],
        )
        self.other_category = Category.objects.create(name="Phones", slug="phones")
        self.criteria = Criteria.objects.create(
            category=self.category,
            name="Battery Life",
        )
        self.product = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="ThinkPad X1 Carbon",
            slug="thinkpad-x1-carbon",
            price=Decimal("1500.00"),
            specs={"ram_gb": 16, "weight_kg": 1.12},
        )
        self.product_2 = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="LOQ 15",
            slug="lenovo-loq-15",
            price=Decimal("950.00"),
            specs={"ram_gb": 16, "weight_kg": 2.4},
        )
        self.phone = Product.objects.create(
            category=self.other_category,
            brand="Samsung",
            name="S24",
            slug="s24",
            price=Decimal("999.00"),
        )

    def test_string_representations(self) -> None:
        self.assertEqual(str(self.category), "Laptops")
        self.assertEqual(str(self.criteria), "Battery Life (Laptops)")
        self.assertEqual(str(self.product), "Lenovo ThinkPad X1 Carbon")

    def test_criteria_unique_constraint_per_category(self) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Criteria.objects.create(category=self.category, name="Battery Life")

        valid_criteria = Criteria.objects.create(
            category=self.other_category, name="Battery Life"
        )
        self.assertEqual(valid_criteria.name, "Battery Life")

    def test_category_deletion_protected_when_products_exist(self) -> None:
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_product_jsonfield_stores_and_queries_specs(self) -> None:
        fetched = Product.objects.get(slug="thinkpad-x1-carbon")
        self.assertEqual(fetched.specs["ram_gb"], 16)
        normalized = fetched.get_normalized_specs()
        self.assertEqual(normalized[0]["display_value"], "16 GB")

    def test_custom_product_queryset_search_and_price_filter(self) -> None:
        results = (
            Product.objects.by_category("laptops")
            .search("thinkpad")
            .by_price_range(min_price=1000, max_price=1600)
        )
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.product)

    def test_product_detail_does_not_leak_reviewer_email(self) -> None:
        """Privacy check: public product detail page must show username/display_name, NEVER user.email."""
        Review.objects.create(
            user=self.user,
            product=self.product,
            overall_rating=9,
            comment="Great keyboard.",
        )
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"product_slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mehrsan")
        self.assertNotContains(response, "private_email@example.com")

    def test_toggle_saved_product_prevents_open_redirect(self) -> None:
        """Security check: passing next='//evil.com' must NOT redirect to external domain."""
        self.client.force_login(self.user)
        url = reverse("catalog:toggle_saved_product", kwargs={"product_slug": self.product.slug})
        response = self.client.post(url, {"next": "//evil.com"})
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, "//evil.com")
        self.assertTrue(SavedProduct.objects.filter(user=self.user, product=self.product).exists())

    def test_compare_view_enforces_same_category_and_detects_identical_specs(self) -> None:
        """Comparing two laptops and a phone must exclude the phone and detect identical RAM."""
        url = reverse("catalog:product_compare")
        response = self.client.get(
            url,
            {"p": [self.product.slug, self.product_2.slug, self.phone.slug]},
        )
        self.assertEqual(response.status_code, 200)
        matrix = response.context["matrix"]
        self.assertTrue(matrix["cross_category_warning"])
        self.assertEqual(len(matrix["products"]), 2)
        self.assertEqual(matrix["identical_spec_count"], 1)  # Both have ram_gb=16
