from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User, UserPreference


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "first_name", "last_name", "is_staff", "is_active", "created_at")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Email & Profile", {"fields": ("email", "first_name", "last_name")}),
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_category", "default_budget", "theme_mode")
    list_select_related = ("user", "preferred_category")
