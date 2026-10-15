from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from catalog.models import Criteria, Product
from core.models import TimeStampedModel


class Review(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    overall_rating = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Overall impression score from 1 to 10.",
    )
    pros = models.TextField(
        blank=True,
        help_text="Key strengths experienced with this product.",
    )
    cons = models.TextField(
        blank=True,
        help_text="Key drawbacks or trade-offs noticed.",
    )
    comment = models.TextField(
        blank=True,
        help_text="Detailed written review explaining the user's experience.",
    )

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_product_review",
            )
        ]

    def __str__(self) -> str:
        return f"Review by {self.user} on {self.product}"


class ReviewScore(TimeStampedModel):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="scores",
    )
    criteria = models.ForeignKey(
        Criteria,
        on_delete=models.PROTECT,
        related_name="review_scores",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Score from 1 (lowest) to 10 (highest).",
    )

    class Meta:
        verbose_name = "Review Score"
        verbose_name_plural = "Review Scores"
        ordering = ["criteria__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["review", "criteria"],
                name="unique_criteria_per_review",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=1) & Q(score__lte=10),
                name="score_between_1_and_10",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.review_id and self.criteria_id:
            if self.criteria.category_id != self.review.product.category_id:
                raise ValidationError(
                    {
                        "criteria": (
                            f"Criteria '{self.criteria.name}' belongs to category "
                            f"'{self.criteria.category.name}', not "
                            f"'{self.review.product.category.name}'."
                        )
                    }
                )

    def __str__(self) -> str:
        return f"{self.criteria.name}: {self.score}/10"
