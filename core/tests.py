import re
from decimal import Decimal
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Criteria, Product
from recommendations.services import (
    parse_criteria_weights_from_params,
    rank_products_for_category,
)
from reviews.models import Review, ReviewScore

User = get_user_model()


class CoreAndSecurityEdgeCaseTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="auditor",
            email="auditor@example.com",
            password="StrongPassword123!",
        )
        self.cat = Category.objects.create(
            name="Laptops",
            slug="laptops",
            spec_schema=[
                {"key": "ram_gb", "label": "RAM", "unit": "GB", "higher_is_better": True, "group": "Memory"},
            ],
        )
        self.crit = Criteria.objects.create(category=self.cat, name="Performance")
        self.prod = Product.objects.create(
            category=self.cat,
            brand="Lenovo",
            name="LOQ 15",
            slug="lenovo-loq-15",
            price=Decimal("950.00"),
            specs={"ram_gb": 16},
        )

    def test_home_dashboard_renders_200(self) -> None:
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_weight_infinity_and_nan_are_safely_ignored(self) -> None:
        weights = parse_criteria_weights_from_params(
            {f"weight_{self.crit.id}": "inf", "weight_999": "nan"}
        )
        self.assertEqual(weights, {})
        ranked = rank_products_for_category(self.cat, weights=weights)
        self.assertEqual(len(ranked), 1)

    def test_custom_user_admin_add_fieldsets_includes_email(self) -> None:
        user_admin = admin.site._registry[User]
        flattened_fields = [
            field
            for _, opts in user_admin.get_fieldsets(None, None)
            for field in opts.get("fields", ())
        ]
        self.assertIn("email", flattened_fields)

    def test_all_pages_extend_base_and_have_clean_short_title(self) -> None:
        self.client.force_login(self.user)
        urls = [
            reverse("home"),
            reverse("catalog:product_search"),
            reverse("catalog:product_compare") + f"?p={self.prod.slug}",
            reverse("catalog:product_detail", kwargs={"product_slug": self.prod.slug}),
            reverse("recommendations:category_recommendations", kwargs={"category_slug": self.cat.slug}),
            reverse("dashboard"),
            reverse("journal_list"),
            reverse("accounts:profile"),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Failed on {url}")
            html = resp.content.decode("utf-8")
            self.assertIn("<!DOCTYPE html>", html, f"Missing DOCTYPE on {url}")
            self.assertIn('class="navbar"', html, f"Missing navbar on {url}")
            m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
            self.assertIsNotNone(m, f"Missing <title> on {url}")
            self.assertLess(len(m.group(1).strip()), 120, f"<title> corrupted on {url}")

    def test_catalog_search_rejects_nan_and_infinity_prices_gracefully(self) -> None:
        url = reverse("catalog:product_search")
        for bad_val in ("NaN", "Infinity", "-Infinity", "abc"):
            resp = self.client.get(url, {"min_price": bad_val, "max_price": bad_val, "min_score": bad_val})
            self.assertEqual(resp.status_code, 200)

    def test_catalog_search_sorting_and_pagination(self) -> None:
        Product.objects.create(
            category=self.cat,
            brand="Apple",
            name="MacBook Air",
            slug="macbook-air",
            price=Decimal("1299.00"),
            specs={"ram_gb": 16},
        )
        resp_asc = self.client.get(reverse("catalog:product_search"), {"sort": "price_asc"})
        self.assertEqual(resp_asc.status_code, 200)
        items_asc = list(resp_asc.context["products"])
        self.assertEqual(items_asc[0].slug, "lenovo-loq-15")

        resp_desc = self.client.get(reverse("catalog:product_search"), {"sort": "price_desc"})
        items_desc = list(resp_desc.context["products"])
        self.assertEqual(items_desc[0].slug, "macbook-air")

    @override_settings(DEBUG=True)
    def test_seed_data_does_not_delete_custom_admin_criteria_or_user_reviews(self) -> None:
        custom_crit = Criteria.objects.create(category=self.cat, name="Linux Compatibility")
        rev = Review.objects.create(
            user=self.user,
            product=self.prod,
            overall_rating=10,
            pros="Flawless Debian 12 support",
        )
        score = ReviewScore.objects.create(review=rev, criteria=custom_crit, score=10)

        call_command("seed_data")
        self.assertTrue(Criteria.objects.filter(id=custom_crit.id).exists())
        self.assertTrue(ReviewScore.objects.filter(id=score.id).exists())

    def test_product_clean_validates_specs_against_category_schema(self) -> None:
        bad_key_prod = Product(
            category=self.cat,
            brand="Test",
            name="BadKey",
            slug="bad-key",
            specs={"unknown_spec": 123},
        )
        with self.assertRaises(ValidationError):
            bad_key_prod.full_clean()

        bad_type_prod = Product(
            category=self.cat,
            brand="Test",
            name="BadType",
            slug="bad-type",
            specs={"ram_gb": "not-a-number"},
        )
        with self.assertRaises(ValidationError):
            bad_type_prod.full_clean()

    def test_smart_summary_takes_pro_from_best_review_and_con_from_lowest_review(self) -> None:
        critic = User.objects.create_user(
            username="critic", email="critic@example.com", password="StrongPassword123!"
        )
        happy = Review.objects.create(
            user=self.user,
            product=self.prod,
            overall_rating=10,
            pros="Whisper-quiet dual cooling fans",
            cons="Minor fingerprint magnet",
        )
        ReviewScore.objects.create(review=happy, criteria=self.crit, score=9)
        unhappy = Review.objects.create(
            user=critic,
            product=self.prod,
            overall_rating=4,
            pros="Decent keyboard",
            cons="Heavy 230W charger brick",
        )
        ReviewScore.objects.create(review=unhappy, criteria=self.crit, score=5)

        summary = rank_products_for_category(self.cat)[0].smart_summary
        self.assertEqual(summary["written_pro"], "Whisper-quiet dual cooling fans")
        self.assertEqual(summary["written_con"], "Heavy 230W charger brick")
        self.assertTrue(any("Whisper-quiet dual cooling fans" in p for p in summary["pros"]))
        self.assertTrue(any("Heavy 230W charger brick" in c for c in summary["cons"]))

    def test_recommendations_json_api_endpoint(self) -> None:
        rev = Review.objects.create(user=self.user, product=self.prod, overall_rating=9)
        ReviewScore.objects.create(review=rev, criteria=self.crit, score=9)
        url = reverse(
            "recommendations:category_recommendations_api",
            kwargs={"category_slug": self.cat.slug},
        )
        resp = self.client.get(url, {f"weight_{self.crit.id}": "10"})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["category"]["slug"], "laptops")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["slug"], "lenovo-loq-15")
        self.assertEqual(payload["results"][0]["match_percentage"], 90)

    @override_settings(DEBUG=False)
    def test_seed_data_refuses_to_run_when_debug_is_false_without_force(self) -> None:
        with self.assertRaises(CommandError):
            call_command("seed_data")

    def test_logout_post_succeeds_and_get_returns_405(self) -> None:
        self.client.force_login(self.user)
        get_resp = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_resp.status_code, 405)

        post_resp = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(post_resp, reverse("home"))

    def test_http_method_guards_return_405_on_wrong_verbs(self) -> None:
        self.client.force_login(self.user)
        api_url = reverse(
            "recommendations:category_recommendations_api",
            kwargs={"category_slug": self.cat.slug},
        )
        self.assertEqual(self.client.post(api_url).status_code, 405)

        del_url = reverse("reviews:delete_review", kwargs={"product_slug": self.prod.slug})
        self.assertEqual(self.client.get(del_url).status_code, 405)

        save_url = reverse("catalog:toggle_saved_product", kwargs={"product_slug": self.prod.slug})
        self.assertEqual(self.client.get(save_url).status_code, 405)

        theme_url = reverse("accounts:update_theme")
        self.assertEqual(self.client.get(theme_url).status_code, 405)

    def test_skip_link_and_main_landmark_present_for_accessibility(self) -> None:
        resp = self.client.get(reverse("home"))
        html = resp.content.decode("utf-8")
        self.assertIn('href="#main-content"', html)
        self.assertIn('id="main-content"', html)

    def test_subcriteria_appear_immediately_under_parent_not_alphabetically_misplaced(self) -> None:
        cam = Criteria.objects.create(category=self.cat, name="Camera System")
        disp = Criteria.objects.create(category=self.cat, name="Display Quality")
        lowlight = Criteria.objects.create(
            category=self.cat, name="Low-Light & Zoom", parent=cam
        )
        rev = Review.objects.create(user=self.user, product=self.prod, overall_rating=9)
        ReviewScore.objects.create(review=rev, criteria=cam, score=9)
        ReviewScore.objects.create(review=rev, criteria=disp, score=10)
        ReviewScore.objects.create(review=rev, criteria=lowlight, score=8)

        ranked = rank_products_for_category(self.cat)
        names = [item["name"] for item in ranked[0].criteria_breakdown]
        self.assertEqual(names.index("Low-Light & Zoom"), names.index("Camera System") + 1)
        self.assertLess(names.index("Low-Light & Zoom"), names.index("Display Quality"))

        resp = self.client.get(
            reverse("catalog:product_detail", kwargs={"product_slug": self.prod.slug})
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        scores_section = html[html.index("Scores by criterion") :]
        self.assertLess(
            scores_section.index("Camera System"),
            scores_section.index("Low-Light &amp; Zoom"),
        )
        self.assertLess(
            scores_section.index("Low-Light &amp; Zoom"),
            scores_section.index("Display Quality"),
        )
