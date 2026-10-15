from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "is_staff", "is_active", "created_at")
    search_fields = ("email", "username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")