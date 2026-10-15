from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from catalog.models import Category, Product
from journal.models import DecisionEntry
from reviews.models import Review


def home_view(request: HttpRequest) -> HttpResponse:
    """
    Landing dashboard displaying all product categories with their
    product and criteria counts, plus platform-wide metrics.
    """
    categories = Category.objects.annotate(
        product_count=Count("products", distinct=True),
        criteria_count=Count("criteria", distinct=True),
    )
    context = {
        "categories": categories,
        "total_products": Product.objects.count(),
        "total_reviews": Review.objects.count(),
        "total_decisions": DecisionEntry.objects.count(),
    }
    return render(request, "home.html", context)