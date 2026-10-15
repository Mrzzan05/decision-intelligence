from django.conf import settings
from django.db import models

from catalog.managers import ProductQuerySet
from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Criteria(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="criteria",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcriteria",
        help_text="Optional parent criterion for hierarchical sub-criteria.",
    )
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Criteria"
        verbose_name_plural = "Criteria"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_criteria_per_category",
            )
        ]

    def __str__(self) -> str:
        if self.parent_id:
            return f"{self.parent.name} -> {self.name} ({self.category.name})"
        return f"{self.name} ({self.category.name})"


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    brand = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Approximate market price in USD.",
    )
    description = models.TextField(
        blank=True,
        help_text="Executive summary of the product's positioning and target user.",
    )
    image_url = models.URLField(
        blank=True,
        help_text="Optional product image URL.",
    )
    specs = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible key-value technical specifications (stored as PostgreSQL JSONB).",
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["brand", "name"]

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class SavedProduct(TimeStampedModel):
    """Bookmarks/favorites allowing users to shortlist products for later decision-making."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_products",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )

    class Meta:
        verbose_name = "Saved Product"
        verbose_name_plural = "Saved Products"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_saved_product",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} saved {self.product}"
