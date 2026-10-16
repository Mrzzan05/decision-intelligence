from django.urls import path

from catalog.views import (
    product_compare_view,
    product_detail_view,
    product_search_view,
    toggle_saved_product_view,
)

app_name = "catalog"

urlpatterns = [
    path("", product_search_view, name="product_search"),
    path("compare/", product_compare_view, name="product_compare"),
    path("product/<slug:product_slug>/", product_detail_view, name="product_detail"),
    path("product/<slug:product_slug>/save/", toggle_saved_product_view, name="toggle_saved_product"),
]
