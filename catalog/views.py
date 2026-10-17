from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from catalog.models import Category, Product, SavedProduct
from recommendations.services import (
    build_category_comparison_matrix,
    parse_criteria_weights_from_params,
    rank_products_for_category,
)


def product_search_view(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    raw_min_price = request.GET.get("min_price", "").strip()
    raw_max_price = request.GET.get("max_price", "").strip()
    raw_min_score = request.GET.get("min_score", "").strip()

    min_price = None
    max_price = None
    min_score = None

    try:
        if raw_min_price:
            min_price = Decimal(raw_min_price)
    except InvalidOperation:
        pass

    try:
        if raw_max_price:
            max_price = Decimal(raw_max_price)
    except InvalidOperation:
        pass

    try:
        if raw_min_score:
            min_score = float(raw_min_score)
    except ValueError:
        pass

    products = (
        Product.objects.select_related("category")
        .with_average_scores()
        .search(query)
        .by_category(category_slug)
        .by_price_range(min_price=min_price, max_price=max_price)
    )
    if min_score is not None:
        products = products.filter(average_score__gte=min_score)

    categories = Category.objects.all()
    context = {
        "products": products,
        "categories": categories,
        "query": query,
        "selected_category": category_slug,
        "min_price": raw_min_price,
        "max_price": raw_max_price,
        "min_score": raw_min_score,
    }
    return render(request, "catalog/product_search.html", context)


def product_detail_view(request: HttpRequest, product_slug: str) -> HttpResponse:
    base_product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=product_slug,
    )
    weights = parse_criteria_weights_from_params(request.GET)
    ranked_products = rank_products_for_category(base_product.category, weights=weights)
    product = next((p for p in ranked_products if p.id == base_product.id), base_product)

    reviews = base_product.reviews.select_related("user").prefetch_related("scores__criteria")

    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedProduct.objects.filter(
            user=request.user, product=base_product
        ).exists()

    context = {
        "product": product,
        "criteria_breakdown": getattr(product, "criteria_breakdown", []),
        "smart_summary": getattr(product, "smart_summary", {}),
        "normalized_specs": product.get_normalized_specs(),
        "reviews": reviews,
        "is_saved": is_saved,
    }
    return render(request, "catalog/product_detail.html", context)


def product_compare_view(request: HttpRequest) -> HttpResponse:
    slugs = request.GET.getlist("p")
    weights = parse_criteria_weights_from_params(request.GET)

    fetched_map = {
        p.slug: p
        for p in Product.objects.filter(slug__in=slugs).select_related("category")
    }
    ordered_selected = [fetched_map[s] for s in slugs if s in fetched_map]

    matrix = build_category_comparison_matrix(ordered_selected, weights=weights)
    all_products = Product.objects.select_related("category").all()

    context = {
        "matrix": matrix,
        "compared_products": matrix["products"],
        "all_products": all_products,
        "selected_slugs": [p.slug for p in matrix["products"]],
        "has_custom_weights": bool(weights),
        "weights_query": urlencode({f"weight_{cid}": f"{w:g}" for cid, w in weights.items()}),
    }
    return render(request, "catalog/product_compare.html", context)


@login_required
def toggle_saved_product_view(request: HttpRequest, product_slug: str) -> HttpResponse:
    """Bookmark or unbookmark a product, protecting against Open Redirect attacks."""
    product = get_object_or_404(Product, slug=product_slug)
    if request.method == "POST":
        existing = SavedProduct.objects.filter(user=request.user, product=product)
        if existing.exists():
            existing.delete()
        else:
            SavedProduct.objects.create(user=request.user, product=product)

    raw_next = request.POST.get("next", "")
    if raw_next and url_has_allowed_host_and_scheme(
        url=raw_next,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(raw_next)

    return redirect("catalog:product_detail", product_slug=product.slug)
