from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product
from recommendations.services import parse_criteria_weights_from_params, rank_products_for_category

User = get_user_model()


class CoreAndSecurityEdgeCaseTests(TestCase):
    def test_home_dashboard_renders_200(self) -> None:
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_weight_infinity_and_nan_are_safely_ignored(self) -> None:
        """Passing weight=inf or weight=nan in URL query params must never produce NaN scores."""
        cat = Category.objects.create(name="TestCat", slug="testcat")
        crit = Criteria.objects.create(category=cat, name="Speed")
        Product.objects.create(category=cat, brand="BrandX", name="ModelY", slug="modely")

        weights = parse_criteria_weights_from_params(
            {f"weight_{crit.id}": "inf", "weight_999": "nan"}
        )
        self.assertEqual(weights, {})
        ranked = rank_products_for_category(cat, weights=weights)
        self.assertEqual(len(ranked), 1)

    def test_custom_user_admin_add_fieldsets_includes_email(self) -> None:
        """Admin 'Add user' form must include the unique email field so creating multiple users works."""
        user_admin = admin.site._registry[User]
        flattened_fields = [
            field
            for _, opts in user_admin.get_fieldsets(None, None)
            for field in opts.get("fields", ())
        ]
        self.assertIn("email", flattened_fields)
