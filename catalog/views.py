from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Category, Product, SavedProduct
from recommendations.services import generate_smart_summary, rank_products_for_category
from reviews.models import ReviewScore


def product_search_view(request: HttpRequest) -> HttpResponse:
    """
    Search and filter products across categories by keyword, category,
    price range, and minimum average review score.
    """
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
    """
    Display comprehensive product intelligence: specs, rule-based Smart Summary,
    visual criteria score bars, and structured user reviews.
    """
    product = get_object_or_404(
        Product.objects.select_related("category").with_average_scores(),
        slug=product_slug,
    )
    criteria_list = list(product.category.criteria.select_related("parent").all())

    score_rows = (
        ReviewScore.objects.filter(review__product=product)
        .values("criteria_id")
        .annotate(avg_score=Avg("score"))
    )
    score_map = {r["criteria_id"]: round(float(r["avg_score"]), 2) for r in score_rows}

    criteria_breakdown = [
        {
            "name": c.name,
            "parent_name": c.parent.name if c.parent else None,
            "score": score_map.get(c.id, 0.0),
            "percentage": int(round(score_map.get(c.id, 0.0) * 10)),
        }
        for c in criteria_list
    ]
    smart_summary = generate_smart_summary(criteria_list, score_map)
    reviews = product.reviews.select_related("user").prefetch_related("scores__criteria")

    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedProduct.objects.filter(
            user=request.user, product=product
        ).exists()

    context = {
        "product": product,
        "criteria_breakdown": criteria_breakdown,
        "smart_summary": smart_summary,
        "reviews": reviews,
        "is_saved": is_saved,
    }
    return render(request, "catalog/product_detail.html", context)


def product_compare_view(request: HttpRequest) -> HttpResponse:
    """
    Side-by-side comparison of selected products (via ?p=slug1&p=slug2).
    """
    slugs = request.GET.getlist("p")
    selected_products = list(
        Product.objects.filter(slug__in=slugs)
        .select_related("category")
        .with_average_scores()
    )

    # Enrich each product with Smart Summary and criteria scores
    categories_seen = {p.category for p in selected_products}
    for cat in categories_seen:
        ranked = rank_products_for_category(cat)
        ranked_map = {rp.id: rp for rp in ranked}
        for idx, sp in enumerate(selected_products):
            if sp.id in ranked_map:
                selected_products[idx] = ranked_map[sp.id]

    all_products = Product.objects.select_related("category").all()
    context = {
        "compared_products": selected_products,
        "all_products": all_products,
        "selected_slugs": slugs,
    }
    return render(request, "catalog/product_compare.html", context)


@login_required
def toggle_saved_product_view(request: HttpRequest, product_slug: str) -> HttpResponse:
    """Bookmark or unbookmark a product for the logged-in user's dashboard."""
    product = get_object_or_404(Product, slug=product_slug)
    if request.method == "POST":
        existing = SavedProduct.objects.filter(user=request.user, product=product)
        if existing.exists():
            existing.delete()
        else:
            SavedProduct.objects.create(user=request.user, product=product)
    next_url = request.POST.get("next") or "catalog:product_detail"
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect("catalog:product_detail", product_slug=product.slug)
