from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Product
from reviews.forms import ReviewForm
from reviews.models import Review, ReviewScore


@login_required
def create_or_update_review_view(
    request: HttpRequest,
    product_slug: str,
) -> HttpResponse:
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=product_slug,
    )
    criteria_list = list(product.category.criteria.select_related("parent").all())
    existing_review = Review.objects.filter(
        user=request.user, product=product
    ).first()

    existing_scores: dict[int, int] = {}
    if existing_review:
        existing_scores = {
            s.criteria_id: s.score for s in existing_review.scores.all()
        }

    for crit in criteria_list:
        crit.initial_score = existing_scores.get(crit.id)  # type: ignore[attr-defined]

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=existing_review)
        criteria_errors: list[str] = []
        parsed_scores: dict[int, int] = {}

        for crit in criteria_list:
            raw_val = request.POST.get(f"criteria_{crit.id}", "").strip()
            if not raw_val.isdigit() or not (1 <= int(raw_val) <= 10):
                criteria_errors.append(
                    f"Score for '{crit.name}' must be an integer between 1 and 10."
                )
            else:
                parsed_scores[crit.id] = int(raw_val)
                crit.initial_score = int(raw_val)  # type: ignore[attr-defined]

        if form.is_valid() and not criteria_errors:
            with transaction.atomic():
                review = form.save(commit=False)
                review.user = request.user
                review.product = product
                review.save()

                for crit in criteria_list:
                    ReviewScore.objects.update_or_create(
                        review=review,
                        criteria=crit,
                        defaults={"score": parsed_scores[crit.id]},
                    )
            return redirect("catalog:product_detail", product_slug=product.slug)
    else:
        form = ReviewForm(instance=existing_review)
        criteria_errors = []

    context = {
        "product": product,
        "form": form,
        "criteria_list": criteria_list,
        "criteria_errors": criteria_errors,
        "is_editing": existing_review is not None,
    }
    return render(request, "reviews/review_form.html", context)


@login_required
def delete_review_view(request: HttpRequest, product_slug: str) -> HttpResponse:
    product = get_object_or_404(Product, slug=product_slug)
    if request.method == "POST":
        Review.objects.filter(user=request.user, product=product).delete()
    return redirect("catalog:product_detail", product_slug=product.slug)
