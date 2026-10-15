from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from catalog.models import Category, Product
from core.models import TimeStampedModel


class DecisionEntry(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="decisions",
    )
    chosen_product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="chosen_in_decisions",
    )
    weights_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of criteria weights at the moment the decision was made.",
    )
    rationale = models.TextField(
        help_text="Why this product was selected over alternatives.",
    )
    expected_outcome = models.TextField(
        blank=True,
        help_text="What the user expects before buying/using the product.",
    )
    expected_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Pre-purchase expected satisfaction (1 to 10).",
    )
    actual_experience = models.TextField(
        blank=True,
        help_text="Real-world experience recorded weeks or months after the decision.",
    )
    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Optional post-decision outcome score (1 to 10) recorded later.",
    )

    class Meta:
        verbose_name = "Decision Entry"
        verbose_name_plural = "Decision Entries"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(satisfaction_rating__isnull=True)
                    | (
                        Q(satisfaction_rating__gte=1)
                        & Q(satisfaction_rating__lte=10)
                    )
                ),
                name="journal_satisfaction_between_1_and_10_or_null",
            )
        ]

    @property
    def expectation_gap(self) -> int | None:
        """Difference between actual post-purchase satisfaction and initial expectation."""
        if self.satisfaction_rating is not None and self.expected_rating is not None:
            return self.satisfaction_rating - self.expected_rating
        return None

    def clean(self) -> None:
        super().clean()
        if self.category_id and self.chosen_product_id:
            if self.chosen_product.category_id != self.category_id:
                raise ValidationError(
                    {
                        "chosen_product": (
                            f"Product '{self.chosen_product}' belongs to category "
                            f"'{self.chosen_product.category}', not '{self.category}'."
                        )
                    }
                )

    def __str__(self) -> str:
        return f"{self.user} chose {self.chosen_product} ({self.category.name})"
