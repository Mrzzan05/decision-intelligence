import math
import json
from collections import defaultdict
from collections.abc import Mapping
from typing import Any
from django.db.models import Avg, Count, OuterRef, Q, StdDev, Subquery
from django.db.models.functions import TruncMonth

from catalog.models import Category, Criteria, Product, order_criteria_tree
from reviews.models import Review, ReviewScore

DEFAULT_CRITERIA_WEIGHT: float = 5.0
DEALBREAKER_WEIGHT_THRESHOLD: float = 8.0
DEALBREAKER_SCORE_THRESHOLD: float = 6.0
DEALBREAKER_PENALTY_FACTOR: float = 0.12
MIXED_OPINION_STDDEV_THRESHOLD: float = 1.45

CHART_PALETTE = [
    {"border": "#3b82f6", "bg": "rgba(59, 130, 246, 0.22)"},
    {"border": "#10b981", "bg": "rgba(16, 185, 129, 0.22)"},
    {"border": "#f59e0b", "bg": "rgba(245, 158, 11, 0.22)"},
    {"border": "#ec4899", "bg": "rgba(236, 72, 153, 0.22)"},
]


def script_safe_json(payload: Any) -> str:
    """
    json.dumps() output that is safe to embed inside an HTML <script> block:
    '<', '>' and '&' are escaped so a product/criteria name can never close the tag.
    """
    return (
        json.dumps(payload)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


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

        if math.isfinite(weight_val) and 0.0 <= weight_val <= 10.0:
            weights[int(criteria_id_str)] = weight_val

    return weights


def build_weights_snapshot_by_name(
    category: Category,
    weights: Mapping[int, float] | None = None,
) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for criterion in order_criteria_tree(category.criteria.all()):
        if criterion.parent_id is not None:
            continue
        if weights and criterion.id in weights:
            snapshot[criterion.name] = float(weights[criterion.id])
        else:
            snapshot[criterion.name] = DEFAULT_CRITERIA_WEIGHT
    return snapshot


def generate_smart_summary(
    criteria_list: list[Criteria],
    product_stats: Mapping[int, dict[str, float | int]],
    category_criteria_means: Mapping[int, float],
    effective_weights: Mapping[int, float],
    review_count: int,
) -> dict[str, Any]:
    if review_count == 0 or not product_stats:
        return {
            "pros": [],
            "cons": [],
            "mixed": [],
            "strengths": [],
            "tradeoffs": [],
            "verdict": "Insufficient review data to generate a consensus summary.",
            "review_count": 0,
            "basis_text": "Insufficient data (0 reviews)",
        }

    def get_priority_weight(c: Criteria) -> float:
        lookup_id = c.parent_id if c.parent_id is not None else c.id
        return effective_weights.get(lookup_id, DEFAULT_CRITERIA_WEIGHT)

    sorted_criteria = sorted(
        criteria_list,
        key=lambda c: (get_priority_weight(c), product_stats.get(c.id, {}).get("avg", 0.0)),
        reverse=True,
    )

    pros: list[str] = []
    cons: list[str] = []
    mixed: list[str] = []

    for crit in sorted_criteria:
        stats = product_stats.get(crit.id)
        if not stats:
            continue

        avg = float(stats["avg"])
        stddev = float(stats["stddev"])
        total = int(stats["total"])
        satisfied = int(stats["satisfied"])
        cat_mean = category_criteria_means.get(crit.id, 7.0)

        if total >= 2 and stddev >= MIXED_OPINION_STDDEV_THRESHOLD:
            if len(mixed) < 2:
                mixed.append(f"Opinions are mixed on {crit.name} ({satisfied} of {total} positive)")
            continue

        if avg >= max(7.5, cat_mean) and (satisfied / max(total, 1)) >= 0.7:
            if len(pros) < 3:
                if total >= 2:
                    pros.append(
                        f"Most users are satisfied with {crit.name} ({satisfied} of {total} reviews)"
                    )
                else:
                    pros.append(f"High score in {crit.name} ({avg:.1f}/10)")

        elif avg <= min(6.5, cat_mean - 0.3) or avg < 6.0:
            if len(cons) < 3:
                cons.append(
                    f"{crit.name} is a common complaint among users ({avg:.1f}/10)"
                )

    basis_text = f"Based on {review_count} review{'s' if review_count != 1 else ''}"
    if pros and not cons:
        verdict = f"Strong consensus leader ({basis_text.lower()})."
    elif pros and cons:
        verdict = f"Excels in core priorities with clear trade-offs ({basis_text.lower()})."
    elif mixed:
        verdict = f"User experiences vary by workload ({basis_text.lower()})."
    else:
        verdict = f"Well-rounded performer across category criteria ({basis_text.lower()})."

    return {
        "pros": pros,
        "cons": cons,
        "mixed": mixed,
        "strengths": pros,
        "tradeoffs": cons,
        "verdict": verdict,
        "review_count": review_count,
        "basis_text": basis_text,
    }


def build_chartjs_payload(
    products: list[Product],
    top_criteria: list[Criteria],
) -> str:
    """Serialize product criteria scores into a Chart.js Radar / Grouped Bar JSON payload."""
    labels = [c.name for c in top_criteria]
    datasets = []
    for idx, prod in enumerate(products[:4]):
        palette = CHART_PALETTE[idx % len(CHART_PALETTE)]
        scores_map = getattr(prod, "criteria_scores", {})
        data_points = [round(float(scores_map.get(c.id, 0.0)), 2) for c in top_criteria]
        datasets.append(
            {
                "label": f"{prod.brand} {prod.name}",
                "data": data_points,
                "borderColor": palette["border"],
                "backgroundColor": palette["bg"],
                "pointBackgroundColor": palette["border"],
                "borderWidth": 2,
            }
        )
    return script_safe_json({"labels": labels, "datasets": datasets})


def rank_products_for_category(
    category: Category,
    weights: Mapping[int, float] | None = None,
) -> list[Product]:
    if weights:
        for criteria_id, weight in weights.items():
            if weight < 0:
                raise ValueError(
                    f"Weight for criteria {criteria_id} cannot be negative ({weight})."
                )

    # Query 1: Fetch all criteria for this category
    criteria_list = order_criteria_tree(category.criteria.all())
    top_level_criteria = [c for c in criteria_list if c.parent_id is None]

    # Query 2: Fetch all products in this category with overall average_score & review_count
    products = list(
        Product.objects.filter(category=category)
        .with_average_scores()
        .annotate(
            # Written highlight: pros from the HIGHEST-rated review, cons from the LOWEST-rated one
            # (taking cons from the happiest reviewer would hide the real trade-offs).
            sample_pro=Subquery(
                Review.objects.filter(product_id=OuterRef("pk"))
                .exclude(pros="")
                .order_by("-overall_rating", "-created_at")
                .values("pros")[:1]
            ),
            sample_con=Subquery(
                Review.objects.filter(product_id=OuterRef("pk"))
                .exclude(cons="")
                .order_by("overall_rating", "-created_at")
                .values("cons")[:1]
            ),
        )
        .select_related("category")
    )

    if not products:
        return []

    # Query 3: Single GROUP BY query computing Avg, StdDev, Total Votes, and Satisfied Votes (>= 7)
    aggregated_scores = (
        ReviewScore.objects.filter(review__product__category=category)
        .values("review__product_id", "criteria_id")
        .annotate(
            criteria_avg=Avg("score"),
            criteria_stddev=StdDev("score", sample=False),
            total_votes=Count("id"),
            satisfied_votes=Count("id", filter=Q(score__gte=7)),
        )
    )

    product_stats_map: dict[int, dict[int, dict[str, float | int]]] = defaultdict(dict)
    product_criteria_map: dict[int, dict[int, float]] = defaultdict(dict)
    criteria_totals_across_category: dict[int, list[float]] = defaultdict(list)

    for row in aggregated_scores:
        product_id = row["review__product_id"]
        crit_id = row["criteria_id"]
        avg_val = round(float(row["criteria_avg"] or 0.0), 2)
        stddev_val = round(float(row["criteria_stddev"] or 0.0), 2)
        total_v = int(row["total_votes"] or 0)
        sat_v = int(row["satisfied_votes"] or 0)

        product_criteria_map[product_id][crit_id] = avg_val
        product_stats_map[product_id][crit_id] = {
            "avg": avg_val,
            "stddev": stddev_val,
            "total": total_v,
            "satisfied": sat_v,
        }
        criteria_totals_across_category[crit_id].append(avg_val)

    category_criteria_means: dict[int, float] = {
        cid: round(sum(vals) / len(vals), 2)
        for cid, vals in criteria_totals_across_category.items()
        if vals
    }

    effective_weights: dict[int, float] = {}
    for criterion in top_level_criteria:
        if weights and criterion.id in weights:
            effective_weights[criterion.id] = float(weights[criterion.id])
        else:
            effective_weights[criterion.id] = DEFAULT_CRITERIA_WEIGHT

    for product in products:
        per_criteria_scores = product_criteria_map.get(product.id, {})
        per_criteria_stats = product_stats_map.get(product.id, {})
        product.criteria_scores = per_criteria_scores  # type: ignore[attr-defined]

        product.criteria_breakdown = [  # type: ignore[attr-defined]
            {
                "id": crit.id,
                "name": crit.name,
                "is_subcriterion": crit.parent_id is not None,
                "score": per_criteria_scores.get(crit.id),
                "percentage": int(round(per_criteria_scores.get(crit.id, 0.0) * 10)),
            }
            for crit in criteria_list
        ]

        weighted_sum = 0.0
        active_weight_sum = 0.0
        dealbreakers: list[str] = []

        for criterion in top_level_criteria:
            if criterion.id in per_criteria_scores:
                score_val = per_criteria_scores[criterion.id]
                weight_val = effective_weights[criterion.id]
                weighted_sum += score_val * weight_val
                active_weight_sum += weight_val

                if (
                    weight_val >= DEALBREAKER_WEIGHT_THRESHOLD
                    and score_val < DEALBREAKER_SCORE_THRESHOLD
                ):
                    dealbreakers.append(criterion.name)

        product.dealbreakers = dealbreakers  # type: ignore[attr-defined]
        rev_count = int(getattr(product, "review_count", 0))

        if rev_count == 0 or active_weight_sum == 0.0 and not per_criteria_scores:
            product.has_sufficient_data = False  # type: ignore[attr-defined]
            product.weighted_score = None  # type: ignore[attr-defined]
            product.match_percentage = None  # type: ignore[attr-defined]
        else:
            product.has_sufficient_data = True  # type: ignore[attr-defined]
            if active_weight_sum > 0.0:
                raw_score = weighted_sum / active_weight_sum
            else:
                raw_score = float(product.average_score)

            final_score = round(raw_score, 2)
            penalty_multiplier = max(
                0.5, 1.0 - (len(dealbreakers) * DEALBREAKER_PENALTY_FACTOR)
            )
            match_pct = int(round((final_score / 10.0) * 100 * penalty_multiplier))

            product.weighted_score = final_score  # type: ignore[attr-defined]
            product.match_percentage = match_pct  # type: ignore[attr-defined]

        product.smart_summary = generate_smart_summary(  # type: ignore[attr-defined]
            criteria_list=criteria_list,
            product_stats=per_criteria_stats,
            category_criteria_means=category_criteria_means,
            effective_weights=effective_weights,
            review_count=rev_count,
        )

        written_notes = {
            "pro": str(getattr(product, "sample_pro", "") or "").strip(),
            "con": str(getattr(product, "sample_con", "") or "").strip(),
        }
        product.smart_summary["written_pro"] = written_notes["pro"]
        product.smart_summary["written_con"] = written_notes["con"]
        if written_notes["pro"] and len(product.smart_summary["pros"]) < 3:
            note_pro = f'Reviewer highlight: "{written_notes["pro"]}"'
            if note_pro not in product.smart_summary["pros"]:
                product.smart_summary["pros"].append(note_pro)
        if written_notes["con"] and len(product.smart_summary["cons"]) < 3:
            note_con = f'Reported trade-off: "{written_notes["con"]}"'
            if note_con not in product.smart_summary["cons"]:
                product.smart_summary["cons"].append(note_con)

    products.sort(
        key=lambda p: (
            getattr(p, "has_sufficient_data", False),
            getattr(p, "match_percentage", None) or -1,
            getattr(p, "weighted_score", None) or -1.0,
            getattr(p, "average_score", 0.0),
            getattr(p, "review_count", 0),
        ),
        reverse=True,
    )

    return products


def build_category_comparison_matrix(
    products: list[Product],
    weights: Mapping[int, float] | None = None,
) -> dict[str, Any]:
    if not products:
        return {
            "category": None,
            "products": [],
            "cross_category_warning": False,
            "important_criteria_rows": [],
            "secondary_criteria_rows": [],
            "spec_groups": [],
            "identical_spec_count": 0,
            "chart_data_json": "{}",
        }

    primary_category = products[0].category
    same_cat_products = [p for p in products if p.category_id == primary_category.id][:4]
    cross_category_warning = len(same_cat_products) < len(products)

    ranked_all = rank_products_for_category(primary_category, weights=weights)
    ranked_map = {rp.id: rp for rp in ranked_all}
    enriched_products = [ranked_map.get(p.id, p) for p in same_cat_products]

    advantages_map: dict[int, list[str]] = defaultdict(list)

    # Check lowest price advantage among compared products
    prices = [float(p.price) for p in enriched_products if p.price and p.price > 0]
    if len(prices) >= 2 and min(prices) != max(prices):
        min_p = min(prices)
        max_p = max(prices)
        for p in enriched_products:
            if float(p.price) == min_p:
                savings = int(round(max_p - min_p))
                advantages_map[p.id].append(f"Most affordable option (saves up to USD {savings})")

    top_criteria = [c for c in order_criteria_tree(primary_category.criteria.all()) if c.parent_id is None]
    important_rows = []
    secondary_rows = []

    for crit in top_criteria:
        w = (weights or {}).get(crit.id, DEFAULT_CRITERIA_WEIGHT)
        scores = [
            getattr(p, "criteria_scores", {}).get(crit.id) for p in enriched_products
        ]
        numeric_scores = [s for s in scores if s is not None]
        best_score = (
            max(numeric_scores)
            if len(numeric_scores) >= 2 and max(numeric_scores) != min(numeric_scores)
            else None
        )

        cells = []
        for p in enriched_products:
            sc = getattr(p, "criteria_scores", {}).get(crit.id)
            is_win = best_score is not None and sc == best_score
            if is_win:
                advantages_map[p.id].append(f"Highest score in {crit.name} ({sc}/10)")
            cells.append({"product_id": p.id, "score": sc, "is_winner": is_win})

        row_data = {"criteria": crit, "weight": w, "cells": cells}
        if w >= 6.0:
            important_rows.append(row_data)
        else:
            secondary_rows.append(row_data)

    schema = primary_category.spec_schema or []
    grouped_specs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    identical_count = 0

    for field_def in schema:
        key = field_def["key"]
        label = field_def["label"]
        unit = field_def.get("unit", "")
        higher_is_better = field_def.get("higher_is_better")
        group_name = field_def.get("group", "General")

        raw_values = [(p.specs or {}).get(key) for p in enriched_products]
        non_null_str = {str(v).strip().lower() for v in raw_values if v is not None}
        is_identical = len(enriched_products) >= 2 and len(non_null_str) == 1 and None not in raw_values

        if is_identical:
            identical_count += 1

        winner_val = None
        numeric_vals = [float(v) for v in raw_values if isinstance(v, (int, float))]
        if len(numeric_vals) >= 2 and not is_identical and higher_is_better is not None:
            winner_val = max(numeric_vals) if higher_is_better else min(numeric_vals)

        cells = []
        for p in enriched_products:
            rv = (p.specs or {}).get(key)
            disp = f"{rv} {unit}".strip() if rv is not None else "—"
            is_win = (
                winner_val is not None
                and isinstance(rv, (int, float))
                and float(rv) == winner_val
            )
            if is_win and len(advantages_map[p.id]) < 4:
                direction_word = "Best" if higher_is_better else "Lowest"
                advantages_map[p.id].append(f"{direction_word} {label} ({disp})")
            cells.append({"product_id": p.id, "value": disp, "is_winner": is_win})

        grouped_specs[group_name].append(
            {
                "key": key,
                "label": label,
                "is_identical": is_identical,
                "cells": cells,
            }
        )

    for p in enriched_products:
        p.head_to_head_advantages = advantages_map.get(p.id, [])[:3]  # type: ignore[attr-defined]

    spec_groups = [
        {"group_name": gname, "rows": rows} for gname, rows in grouped_specs.items()
    ]
    chart_data_json = build_chartjs_payload(enriched_products, top_criteria)

    return {
        "category": primary_category,
        "products": enriched_products,
        "cross_category_warning": cross_category_warning,
        "important_criteria_rows": important_rows,
        "secondary_criteria_rows": secondary_rows,
        "spec_groups": spec_groups,
        "identical_spec_count": identical_count,
        "chart_data_json": chart_data_json,
    }


def build_platform_analytics(limit: int = 5) -> dict[str, Any]:
    """
    Platform-wide analytics for the dashboard: popular products, best-rated
    products, review volume per category and review trend per month.
    Runs a fixed number of queries (4) regardless of data size.
    """
    reviewed = Product.objects.select_related("category").with_average_scores().filter(
        review_count__gt=0
    )
    most_reviewed = list(reviewed.order_by("-review_count", "-average_score", "name")[:limit])
    top_rated = list(reviewed.order_by("-average_score", "-review_count", "name")[:limit])

    by_category = list(
        Category.objects.annotate(review_total=Count("products__reviews"))
        .filter(review_total__gt=0)
        .order_by("-review_total", "name")
    )
    monthly = list(
        Review.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )[-6:]

    max_reviews = max((p.review_count for p in most_reviewed), default=0)
    for p in most_reviewed:
        p.popularity_pct = int(round(p.review_count / max_reviews * 100)) if max_reviews else 0
    max_month = max((m["total"] for m in monthly), default=0)
    for m in monthly:
        m["pct"] = int(round(m["total"] / max_month * 100)) if max_month else 0

    return {
        "most_reviewed": most_reviewed,
        "top_rated": top_rated,
        "by_category": by_category,
        "monthly": monthly,
    }
