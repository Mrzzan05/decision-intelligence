from django.contrib import admin

from catalog.models import Category, Criteria, Product, SavedProduct


class CriteriaInline(admin.TabularInline):
    model = Criteria
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [CriteriaInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "price", "slug", "created_at")
    list_filter = ("category", "brand")
    search_fields = ("name", "brand", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("category",)


@admin.register(SavedProduct)
class SavedProductAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    list_select_related = ("user", "product")
