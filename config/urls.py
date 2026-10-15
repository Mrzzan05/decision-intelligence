from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.views import home_view
from journal.views import (
    dashboard_view,
    journal_list_view,
    record_decision_view,
    update_decision_experience_view,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("accounts/", include("accounts.urls")),
    path("catalog/", include("catalog.urls")),
    path("reviews/", include("reviews.urls")),
    path("recommendations/", include("recommendations.urls")),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("journal/", journal_list_view, name="journal_list"),
    path(
        "journal/record/<slug:product_slug>/",
        record_decision_view,
        name="record_decision",
    ),
    path(
        "journal/update/<int:entry_id>/",
        update_decision_experience_view,
        name="update_decision",
    ),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns = [
            path("__debug__/", include("debug_toolbar.urls")),
        ] + urlpatterns
    except ImportError:
        pass
