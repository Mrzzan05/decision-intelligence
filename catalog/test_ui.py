from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product
from reviews.models import Review, ReviewScore

User = get_user_model()


class CatalogUITests(TestCase):
    """Regression tests for compare/detail/search UI behaviour."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="Pass12345!x"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password="Pass12345!x"
        )
        self.cat = Category.objects.create(name="Phones", slug="phones")
        self.camera = Criteria.objects.create(category=self.cat, name="Camera")
        self.battery = Criteria.objects.create(category=self.cat, name="Battery")
        self.a = Product.objects.create(
            category=self.cat, brand="Acme", name="A1", slug="acme-a1", price=500
        )
        self.b = Product.objects.create(
            category=self.cat, brand="Bolt", name="Levi's B2", slug="bolt-b2", price=700
        )
        for product, cam, bat in ((self.a, 9, 5), (self.b, 6, 9)):
            review = Review.objects.create(user=self.user, product=product, overall_rating=8)
            ReviewScore.objects.create(review=review, criteria=self.camera, score=cam)
            ReviewScore.objects.create(review=review, criteria=self.battery, score=bat)
        Review.objects.filter(product=self.a).update()  # keep ownership on self.user

    def _compare_url(self, extra: str = "") -> str:
        return f"{reverse('catalog:product_compare')}?p={self.a.slug}&p={self.b.slug}{extra}"

    def test_compare_shows_criteria_rows_even_with_default_weights(self) -> None:
        """Regression: with neutral weights (5 < 6) every criterion used to be dropped."""
        response = self.client.get(self._compare_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Other Criteria")
        self.assertContains(response, "Camera")
        self.assertContains(response, "Battery")
        self.assertContains(response, "neutral priorities")

    def test_compare_splits_priorities_when_weights_given(self) -> None:
        extra = f"&weight_{self.camera.id}=9&weight_{self.battery.id}=2"
        response = self.client.get(self._compare_url(extra))
        self.assertContains(response, "Your Priorities")
        self.assertContains(response, "Other Criteria")
        self.assertNotContains(response, "neutral priorities")

    def test_compare_decide_links_carry_weights(self) -> None:
        extra = f"&weight_{self.camera.id}=9"
        response = self.client.get(self._compare_url(extra))
        self.assertContains(response, f"weight_{self.camera.id}=9")
        self.assertContains(response, reverse("record_decision", args=[self.a.slug]))

    def test_detail_shows_delete_only_to_review_owner(self) -> None:
        delete_url = reverse("reviews:delete_review", args=[self.a.slug])
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("catalog:product_detail", args=[self.a.slug])), delete_url)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("catalog:product_detail", args=[self.a.slug])), delete_url)

    def test_detail_never_exposes_reviewer_email(self) -> None:
        response = self.client.get(reverse("catalog:product_detail", args=[self.a.slug]))
        self.assertNotContains(response, "owner@example.com")

    def test_detail_renders_for_category_without_spec_schema(self) -> None:
        self.a.specs = {"ram_gb": 16}
        self.a.save()
        response = self.client.get(reverse("catalog:product_detail", args=[self.a.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ram Gb")
        self.assertContains(response, "16")

    def test_search_compare_buttons_escape_names_with_apostrophes(self) -> None:
        """Names are emitted into data-attributes (HTML-escaped), never into inline JS strings."""
        response = self.client.get(reverse("catalog:product_search"))
        self.assertContains(response, "data-compare-slug")
        self.assertContains(response, "Levi&#x27;s")
        self.assertNotContains(response, "toggleCompareTrayItem('")
