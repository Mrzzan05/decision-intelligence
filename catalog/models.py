from typing import Any
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalog.managers import ProductQuerySet
from core.models import TimeStampedModel


class Category(TimeStampedModel):
    """
    Product category defining evaluation criteria, a normalized specification schema,
    and priority presets (e.g., Gamer, Photographer, Daily User).
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    spec_schema = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of normalized spec definitions: "
            "[{'key': 'ram_gb', 'label': 'RAM', 'unit': 'GB', 'higher_is_better': True, 'group': 'Performance'}]"
        ),
    )
    presets = models.JSONField(
        default=dict,
        blank=True,
        help_text="Named weight presets for quick user persona selection.",
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.spec_schema, list):
            raise ValidationError({"spec_schema": "spec_schema must be a list of dictionaries."})
        required_keys = {"key", "label", "unit", "higher_is_better", "group"}
        for item in self.spec_schema:
            if not isinstance(item, dict) or not required_keys.issubset(item.keys()):
                raise ValidationError(
                    {
                        "spec_schema": (
                            "Each schema item must contain: key, label, unit, higher_is_better, group."
                        )
                    }
                )

    def __str__(self) -> str:
        return self.name


class Criteria(TimeStampedModel):
    """
    Evaluation dimension for a Category.
    Top-level criteria (parent=None) carry user weights in the ranking engine.
    Sub-criteria (parent!=None) provide granular diagnostics for Smart Summaries.
    """

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
        help_text="Market price in USD.",
    )
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    specs = models.JSONField(
        default=dict,
        blank=True,
        help_text="Normalized key-value technical specifications matching category.spec_schema.",
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["brand", "name"]

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.specs, dict):
            raise ValidationError({"specs": "Specifications must be a valid JSON object (dictionary)."})
        if self.category_id and self.category.spec_schema:
            schema_map = {
                item["key"]: item
                for item in self.category.spec_schema
                if isinstance(item, dict) and "key" in item
            }
            unknown_keys = sorted(set(self.specs.keys()) - set(schema_map.keys()))
            if unknown_keys:
                raise ValidationError(
                    {
                        "specs": (
                            f"Unknown specification keys for category '{self.category.name}': "
                            f"{', '.join(unknown_keys)}."
                        )
                    }
                )
            for key, val in self.specs.items():
                if val is None:
                    continue
                field_def = schema_map.get(key, {})
                if field_def.get("higher_is_better") is not None:
                    if isinstance(val, bool) or not isinstance(val, (int, float)):
                        raise ValidationError(
                            {"specs": f"Specification '{key}' must be a numeric value."}
                        )

    def get_normalized_specs(self) -> list[dict[str, Any]]:
        """Return product specifications ordered and formatted by category.spec_schema."""
        schema = self.category.spec_schema or []
        if not schema:
            return [
                {
                    "key": k,
                    "label": k.replace("_", " ").title(),
                    "raw_value": v,
                    "display_value": str(v),
                    "unit": "",
                    "higher_is_better": None,
                    "group": "General",
                }
                for k, v in (self.specs or {}).items()
            ]
        normalized = []
        for field_def in schema:
            key = field_def["key"]
            raw_val = (self.specs or {}).get(key)
            unit = field_def.get("unit", "")
            display_val = f"{raw_val} {unit}".strip() if raw_val is not None else "—"
            normalized.append(
                {
                    "key": key,
                    "label": field_def["label"],
                    "raw_value": raw_val,
                    "display_value": display_val,
                    "unit": unit,
                    "higher_is_better": field_def.get("higher_is_better"),
                    "group": field_def.get("group", "General"),
                }
            )
        return normalized

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class SavedProduct(TimeStampedModel):
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
        return f"{self.user.username} saved {self.product}"


def order_criteria_tree(criteria_iterable):
    """Order criteria hierarchically: each top-level parent followed immediately by its sub-criteria."""
    items = list(criteria_iterable)
    by_id = {c.id: c for c in items}
    children_map: dict[int | None, list] = {}
    for c in items:
        parent_key = c.parent_id if (c.parent_id and c.parent_id in by_id) else None
        children_map.setdefault(parent_key, []).append(c)

    for group in children_map.values():
        group.sort(key=lambda x: x.name.lower())

    ordered = []
    visited: set[int] = set()

    def _visit(node) -> None:
        if node.id in visited:
            return
        visited.add(node.id)
        ordered.append(node)
        for child in children_map.get(node.id, []):
            _visit(child)

    for root in children_map.get(None, []):
        _visit(root)

    for leftover in items:
        if leftover.id not in visited:
            ordered.append(leftover)

    return ordered
