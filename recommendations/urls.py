from django.urls import path

from recommendations.views import category_recommendations_view

app_name = "recommendations"

urlpatterns = [
    path(
        "<slug:category_slug>/",
        category_recommendations_view,
        name="category_recommendations",
    ),
]