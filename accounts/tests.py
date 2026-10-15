from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserPreference

User = get_user_model()


class AuthenticationAndProfileTests(TestCase):
    def test_unauthenticated_journal_redirects_to_accounts_login(self) -> None:
        """Visiting /journal/ while logged out must redirect (302) to /accounts/login/, not 404."""
        response = self.client.get(reverse("journal_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_signup_creates_user_and_preference(self) -> None:
        """Signing up creates both a User and a linked UserPreference."""
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "newstudent@example.com",
                "username": "newstudent",
                "first_name": "Ali",
                "last_name": "Rezaei",
                "password1": "StrongPass123!@#",
                "password2": "StrongPass123!@#",
            },
        )
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(email="newstudent@example.com")
        self.assertTrue(UserPreference.objects.filter(user=user).exists())