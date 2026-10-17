from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Criteria, Product

User = get_user_model()


class ReviewFormUXTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="rv", email="rv@example.com", password="Pass12345!x")
        self.cat = Category.objects.create(name="Phones", slug="phones")
        self.crit = Criteria.objects.create(category=self.cat, name="Camera")
        self.product = Product.objects.create(category=self.cat, brand="A", name="One", slug="a-one", price=1)
        self.url = reverse("reviews:write_review", args=[self.product.slug])
        self.client.force_login(self.user)

    def test_new_review_form_is_not_prefilled_with_scores(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="8"')

    def test_invalid_criteria_score_shows_visible_error(self) -> None:
        response = self.client.post(
            self.url, {"overall_rating": "8", f"criteria_{self.crit.id}": "15"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "must be an integer between 1 and 10")
