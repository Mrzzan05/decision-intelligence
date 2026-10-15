from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Product, SavedProduct
from journal.forms import DecisionEntryForm
from journal.models import DecisionEntry
from recommendations.services import (
    build_weights_snapshot_by_name,
    parse_criteria_weights_from_params,
)


@login_required
def journal_list_view(request: HttpRequest) -> HttpResponse:
    entries = (
        DecisionEntry.objects.filter(user=request.user)
        .select_related("category", "chosen_product")
    )
    return render(request, "journal/journal_list.html", {"entries": entries})


@login_required
def record_decision_view(request: HttpRequest, product_slug: str) -> HttpResponse:
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=product_slug,
    )

    raw_params = request.POST if request.method == "POST" else request.GET
    parsed_weights = parse_criteria_weights_from_params(raw_params)
    weights_snapshot = build_weights_snapshot_by_name(product.category, parsed_weights)

    weight_hidden_fields = {
        f"weight_{crit.id}": parsed_weights.get(crit.id, 5.0)
        for crit in product.category.criteria.all()
        if crit.parent_id is None
    }

    if request.method == "POST":
        form = DecisionEntryForm(request.POST)
        form.instance.user = request.user
        form.instance.category = product.category
        form.instance.chosen_product = product
        form.instance.weights_snapshot = weights_snapshot

        if form.is_valid():
            form.save()
            return redirect("journal_list")
    else:
        form = DecisionEntryForm()

    context = {
        "product": product,
        "form": form,
        "weights_snapshot": weights_snapshot,
        "weight_hidden_fields": weight_hidden_fields,
    }
    return render(request, "journal/record_decision.html", context)


@login_required
def update_decision_experience_view(
    request: HttpRequest,
    entry_id: int,
) -> HttpResponse:
    entry = get_object_or_404(
        DecisionEntry.objects.select_related("category", "chosen_product"),
        pk=entry_id,
        user=request.user,
    )

    if request.method == "POST":
        form = DecisionEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect("journal_list")
    else:
        form = DecisionEntryForm(instance=entry)

    context = {
        "product": entry.chosen_product,
        "form": form,
        "weights_snapshot": entry.weights_snapshot,
        "weight_hidden_fields": {},
        "is_updating": True,
    }
    return render(request, "journal/record_decision.html", context)


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    decisions = list(
        DecisionEntry.objects.filter(user=request.user)
        .select_related("category", "chosen_product")
    )
    saved_products = (
        SavedProduct.objects.filter(user=request.user)
        .select_related("product__category")
    )
    user_reviews = request.user.reviews.select_related("product__category")

    aggs = DecisionEntry.objects.filter(user=request.user).aggregate(
        avg_expected=Avg("expected_rating"),
        avg_actual=Avg("satisfaction_rating"),
    )

    context = {
        "decisions": decisions,
        "saved_products": saved_products,
        "user_reviews": user_reviews,
        "avg_expected": round(float(aggs["avg_expected"] or 0.0), 1),
        "avg_actual": round(float(aggs["avg_actual"] or 0.0), 1),
        "decision_count": len(decisions),
    }
    return render(request, "journal/dashboard.html", context)
