from django.contrib import admin

from reviews.models import Review, ReviewScore


class ReviewScoreInline(admin.TabularInline):
    model = ReviewScore
    extra = 1


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "created_at")
    list_filter = ("product__category", "created_at")
    search_fields = ("product__name", "user__email", "comment")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("product", "user")
    inlines = [ReviewScoreInline]