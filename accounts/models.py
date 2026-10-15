from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """
    Custom user model using email as the primary authentication identifier
    instead of username, while inheriting audit timestamps.
    """

    email = models.EmailField(
        unique=True,
        help_text="Required. Used as the primary login identifier.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email


class UserPreference(TimeStampedModel):
    """
    Stores a user's personal decision-making preferences and UI settings.
    """

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
    dark_mode = models.BooleanField(
        default=False,
        help_text="Enable dark theme across the platform.",
    )

    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"

    def __str__(self) -> str:
        return f"Preferences for {self.user.email}"