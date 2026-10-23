from django.urls import path

from recommendations.views import (
    category_recommendations_api_view,
    category_recommendations_view,
)

app_name = "recommendations"

urlpatterns = [
    path(
        "api/<slug:category_slug>/",
        category_recommendations_api_view,
        name="category_recommendations_api",
    ),
    path(
        "<slug:category_slug>/",
        category_recommendations_view,
        name="category_recommendations",
    ),
]
