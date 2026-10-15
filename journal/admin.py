from django.contrib import admin

from journal.models import DecisionEntry


@admin.register(DecisionEntry)
class DecisionEntryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "category",
        "chosen_product",
        "satisfaction_rating",
        "created_at",
    )
    list_filter = ("category", "satisfaction_rating", "created_at")
    search_fields = (
        "user__email",
        "chosen_product__name",
        "chosen_product__brand",
        "rationale",
    )
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user", "category", "chosen_product")