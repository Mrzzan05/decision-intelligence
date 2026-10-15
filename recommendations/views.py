import json
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
    Thin view coordinating HTTP params, persona presets, and live ranking context.
    Only top-level criteria (parent_id=None) are exposed as weight sliders.
    """
    category = get_object_or_404(Category, slug=category_slug)
    weights = parse_criteria_weights_from_params(request.GET)
    ranked_products = rank_products_for_category(category=category, weights=weights)

    top_criteria = [c for c in category.criteria.all() if c.parent_id is None]
    name_to_id = {c.name: c.id for c in top_criteria}

    for criterion in top_criteria:
        criterion.current_weight = weights.get(criterion.id, DEFAULT_CRITERIA_WEIGHT)  # type: ignore[attr-defined]

    # Map category presets from criteria names to input IDs (weight_<id>)
    ui_presets = []
    for preset_key, preset_data in (category.presets or {}).items():
        mapped_weights = {}
        for c_name, w_val in preset_data.get("weights", {}).items():
            if c_name in name_to_id:
                mapped_weights[f"weight_{name_to_id[c_name]}"] = w_val
        ui_presets.append(
            {
                "key": preset_key,
                "label": preset_data.get("label", preset_key.title()),
                "weights_json": json.dumps(mapped_weights),
            }
        )

    best_match = ranked_products[0] if ranked_products and getattr(ranked_products[0], "has_sufficient_data", False) else None

    context = {
        "category": category,
        "criteria_list": top_criteria,
        "products": ranked_products,
        "best_match": best_match,
        "ui_presets": ui_presets,
        "weights": weights,
        "query_string": request.GET.urlencode(),
    }
    return render(request, "recommendations/category_recommendations.html", context)
