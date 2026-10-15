from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from catalog.models import Category, Criteria, Product


class CatalogModelTests(TestCase):
    def setUp(self) -> None:
        self.category = Category.objects.create(
            name="Laptops",
            slug="laptops",
        )
        self.criteria = Criteria.objects.create(
            category=self.category,
            name="Battery Life",
        )
        self.product = Product.objects.create(
            category=self.category,
            brand="Lenovo",
            name="ThinkPad X1 Carbon",
            slug="thinkpad-x1-carbon",
            specs={"ram_gb": 32, "storage_tb": 1, "oled": True},
        )

    def test_string_representations(self) -> None:
        """Verify __str__ methods return human-readable identifiers."""
        self.assertEqual(str(self.category), "Laptops")
        self.assertEqual(str(self.criteria), "Battery Life (Laptops)")
        self.assertEqual(str(self.product), "Lenovo ThinkPad X1 Carbon")

    def test_criteria_unique_constraint_per_category(self) -> None:
        """
        Verify that duplicate criteria names within the same category raise IntegrityError,
        while the same criteria name in a different category is allowed.
        """
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Criteria.objects.create(
                    category=self.category,
                    name="Battery Life",
                )

        # Because we wrapped the expected failure in transaction.atomic(),
        # we can safely execute subsequent database queries in the same test!
        other_category = Category.objects.create(name="Smartphones", slug="smartphones")
        valid_criteria = Criteria.objects.create(
            category=other_category,
            name="Battery Life",
        )
        self.assertEqual(valid_criteria.name, "Battery Life")

    def test_category_deletion_protected_when_products_exist(self) -> None:
        """Verify that deleting a Category with existing Products raises ProtectedError."""
        with self.assertRaises(ProtectedError):
            self.category.delete()

        # Verify that if products are removed, deleting Category cascades to Criteria
        self.product.delete()
        self.category.delete()
        self.assertEqual(Criteria.objects.count(), 0)

    def test_product_jsonfield_stores_and_queries_specs(self) -> None:
        """Verify PostgreSQL JSONB storage and key lookup."""
        fetched = Product.objects.get(slug="thinkpad-x1-carbon")
        self.assertEqual(fetched.specs["ram_gb"], 32)
        self.assertTrue(fetched.specs["oled"])

        # Test PostgreSQL JSONB nested lookup
        high_ram_products = Product.objects.filter(specs__ram_gb=32)
        self.assertIn(self.product, high_ram_products)

    def test_custom_product_queryset_methods(self) -> None:
        """Verify custom QuerySet chaining (by_category and search)."""
        results = Product.objects.by_category("laptops").search("thinkpad")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.product)