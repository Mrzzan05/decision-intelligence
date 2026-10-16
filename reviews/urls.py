from django.urls import path

from reviews.views import create_or_update_review_view, delete_review_view

app_name = "reviews"

urlpatterns = [
    path("<slug:product_slug>/write/", create_or_update_review_view, name="write_review"),
    path("<slug:product_slug>/delete/", delete_review_view, name="delete_review"),
]
