from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserPreference

User = get_user_model()


class AuthenticationAndProfileTests(TestCase):
    def test_unauthenticated_journal_redirects_to_accounts_login(self) -> None:
        response = self.client.get(reverse("journal_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_signup_creates_user_and_preference(self) -> None:
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

    def test_theme_mode_endpoint_persists_to_user_preference(self) -> None:
        """Clicking the theme switcher updates UserPreference.theme_mode in PostgreSQL."""
        user = User.objects.create_user(
            username="themeuser", email="theme@example.com", password="Password123!"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:update_theme"), {"theme_mode": "dark"}
        )
        self.assertEqual(response.status_code, 200)
        pref = UserPreference.objects.get(user=user)
        self.assertEqual(pref.theme_mode, "dark")
        self.assertTrue(pref.dark_mode)

    def test_user_display_name_hides_email(self) -> None:
        user = User.objects.create_user(
            username="safe_handle", email="secret@example.com", password="Password123!"
        )
        self.assertEqual(user.display_name, "safe_handle")
        self.assertNotIn("@", user.display_name)
