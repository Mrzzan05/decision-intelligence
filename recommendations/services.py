from collections import defaultdict
from collections.abc import Mapping
from typing import Any
from django.db.models import Avg

from catalog.models import Category, Criteria, Product
from reviews.models import ReviewScore

DEFAULT_CRITERIA_WEIGHT: float = 5.0


def parse_criteria_weights_from_params(
    query_params: Mapping[str, str],
) -> dict[int, float]:
    weights: dict[int, float] = {}
    prefix = "weight_"

    for key, raw_value in query_params.items():
        if not key.startswith(prefix):
            continue
        criteria_id_str = key[len(prefix) :]
        if not criteria_id_str.isdigit():
            continue
        try:
            weight_val = float(raw_value)
        except (TypeError, ValueError):
            continue

        if 0.0 <= weight_val <= 10.0:
            weights[int(criteria_id_str)] = weight_val

    return weights


def build_weights_snapshot_by_name(
    category: Category,
    weights: Mapping[int, float] | None = None,
) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for criterion in category.criteria.all():
        if weights and criterion.id in weights:
            snapshot[criterion.name] = float(weights[criterion.id])
        else:
            snapshot[criterion.name] = DEFAULT_CRITERIA_WEIGHT
    return snapshot


def generate_smart_summary(
    criteria_list: list[Criteria],
    per_criteria_scores: Mapping[int, float],
) -> dict[str, Any]:
    """
    Rule-based Smart Summary generator (zero external AI dependency).
    Classifies criteria with avg >= 8.0 as Strengths, <= 6.0 as Trade-offs,
    and generates an executive verdict.
    """
    strengths: list[str] = []
    tradeoffs: list[str] = []

    for crit in criteria_list:
        score = per_criteria_scores.get(crit.id)
        if score is None:
            continue
        if score >= 8.0:
            strengths.append(f"{crit.name} ({score:.1f}/10)")
        elif score <= 6.0:
            tradeoffs.append(f"{crit.name} ({score:.1f}/10)")

    if strengths and not tradeoffs:
        verdict = "All-round top performer with no major weaknesses."
    elif strengths and tradeoffs:
        verdict = f"Excels in {strengths[0].split(' (')[0]}, with trade-offs in {tradeoffs[0].split(' (')[0]}."
    elif tradeoffs:
        verdict = "Budget or specialized option with notable performance trade-offs."
    else:
        verdict = "Balanced mid-tier performance across evaluated criteria."

    return {
        "strengths": strengths,
        "tradeoffs": tradeoffs,
        "verdict": verdict,
    }


def rank_products_for_category(
    category: Category,
    weights: Mapping[int, float] | None = None,
) -> list[Product]:
    """
    Rank all products in a given Category using Weighted Multi-Criteria Scoring.
    Executes in a constant O(1) number of SQL queries (exactly 3 queries).
    """
    if weights:
        for criteria_id, weight in weights.items():
            if weight < 0:
                raise ValueError(
                    f"Weight for criteria {criteria_id} cannot be negative ({weight})."
                )

    # Query 1: Fetch all valid criteria for this category
    criteria_list = list(category.criteria.all())

    # Query 2: Fetch all products in this category with overall average_score & review_count
    products = list(
        Product.objects.filter(category=category)
        .with_average_scores()
        .select_related("category")
    )

    if not products:
        return []

    # Query 3: Single GROUP BY query to get average score per (product_id, criteria_id)
    aggregated_scores = (
        ReviewScore.objects.filter(review__product__category=category)
        .values("review__product_id", "criteria_id")
        .annotate(criteria_avg=Avg("score"))
    )

    product_criteria_map: dict[int, dict[int, float]] = defaultdict(dict)
    for row in aggregated_scores:
        product_id = row["review__product_id"]
        crit_id = row["criteria_id"]
        product_criteria_map[product_id][crit_id] = round(float(row["criteria_avg"]), 2)

    effective_weights: dict[int, float] = {}
    for criterion in criteria_list:
        if weights and criterion.id in weights:
            effective_weights[criterion.id] = float(weights[criterion.id])
        else:
            effective_weights[criterion.id] = DEFAULT_CRITERIA_WEIGHT

    for product in products:
        per_criteria_scores = product_criteria_map.get(product.id, {})
        product.criteria_scores = per_criteria_scores  # type: ignore[attr-defined]
        product.criteria_breakdown = [  # type: ignore[attr-defined]
            {
                "name": crit.name,
                "score": per_criteria_scores.get(crit.id, 0.0),
                "percentage": int(round(per_criteria_scores.get(crit.id, 0.0) * 10)),
            }
            for crit in criteria_list
        ]
        product.smart_summary = generate_smart_summary(  # type: ignore[attr-defined]
            criteria_list, per_criteria_scores
        )

        weighted_sum = 0.0
        active_weight_sum = 0.0

        for criterion in criteria_list:
            if criterion.id in per_criteria_scores:
                score_val = per_criteria_scores[criterion.id]
                weight_val = effective_weights[criterion.id]
                weighted_sum += score_val * weight_val
                active_weight_sum += weight_val

        if active_weight_sum > 0.0:
            final_score = round(weighted_sum / active_weight_sum, 2)
        else:
            final_score = round(float(product.average_score), 2)

        product.weighted_score = final_score  # type: ignore[attr-defined]
        product.match_percentage = int(round((final_score / 10.0) * 100))  # type: ignore[attr-defined]

    products.sort(
        key=lambda p: (
            getattr(p, "weighted_score", 0.0),
            getattr(p, "average_score", 0.0),
            getattr(p, "review_count", 0),
        ),
        reverse=True,
    )

    return products
