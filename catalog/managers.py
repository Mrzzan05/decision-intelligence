from decimal import Decimal, InvalidOperation
from typing import Self
from django.db import models
from django.db.models import Avg, Count, FloatField, Q
from django.db.models.functions import Coalesce


def _to_finite_decimal(val: Decimal | float | str | None) -> Decimal | None:
    if val is None:
        return None
    try:
        d = val if isinstance(val, Decimal) else Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d.is_finite() else None


class ProductQuerySet(models.QuerySet):
    def by_category(self, category_slug: str) -> Self:
        if not category_slug:
            return self
        return self.filter(category__slug=category_slug)

    def search(self, query: str) -> Self:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return self
        return self.filter(
            Q(name__icontains=cleaned_query)
            | Q(brand__icontains=cleaned_query)
            | Q(description__icontains=cleaned_query)
        )

    def by_price_range(
        self,
        min_price: Decimal | float | None = None,
        max_price: Decimal | float | None = None,
    ) -> Self:
        qs = self
        safe_min = _to_finite_decimal(min_price)
        safe_max = _to_finite_decimal(max_price)
        if safe_min is not None:
            qs = qs.filter(price__gte=safe_min)
        if safe_max is not None:
            qs = qs.filter(price__lte=safe_max)
        return qs

    def with_average_scores(self) -> Self:
        return self.annotate(
            average_score=Coalesce(
                Avg("reviews__scores__score"),
                0.0,
                output_field=FloatField(),
            ),
            review_count=Count("reviews", distinct=True),
        )
