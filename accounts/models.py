from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    email = models.EmailField(
        unique=True,
        help_text="Required. Used as the primary login identifier.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    @property
    def display_name(self) -> str:
        """Publicly safe display name that never leaks the user's email address."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def __str__(self) -> str:
        return self.email


class UserPreference(TimeStampedModel):
    THEME_SYSTEM = "system"
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_SYSTEM, "System Default"),
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preference",
    )
    preferred_category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_by_users",
    )
    default_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="User's target maximum budget for product recommendations.",
    )
    theme_mode = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default=THEME_SYSTEM,
        help_text="Preferred UI color scheme (System, Light, or Dark).",
    )
    dark_mode = models.BooleanField(
        default=False,
        help_text="Legacy boolean flag synced with theme_mode.",
    )

    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"

    def __str__(self) -> str:
        return f"Preferences for {self.user.username}"
