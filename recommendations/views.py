from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from catalog.models import Category
from recommendations.services import (
    DEFAULT_CRITERIA_WEIGHT,
    parse_criteria_weights_from_params,
    rank_products_for_category,
)


def category_recommendations_view(
    request: HttpRequest,
    category_slug: str,
) -> HttpResponse:
    """
    Thin view that coordinates HTTP input/output while delegating
    all ranking and scoring computation to the service layer.
    """
    category = get_object_or_404(Category, slug=category_slug)
    weights = parse_criteria_weights_from_params(request.GET)
    ranked_products = rank_products_for_category(category=category, weights=weights)
    criteria_list = list(category.criteria.all())

    for criterion in criteria_list:
        criterion.current_weight = weights.get(criterion.id, DEFAULT_CRITERIA_WEIGHT)  # type: ignore[attr-defined]

    context = {
        "category": category,
        "criteria_list": criteria_list,
        "products": ranked_products,
        "weights": weights,
        "query_string": request.GET.urlencode(),
    }
    return render(request, "recommendations/category_recommendations.html", context)