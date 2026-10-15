from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from accounts.forms import (
    CustomUserCreationForm,
    EmailAuthenticationForm,
    UserPreferenceForm,
    UserProfileForm,
)
from accounts.models import UserPreference


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = "home"


def signup_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserPreference.objects.get_or_create(user=user)
            login(request, user)
            return redirect("home")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    preference, _ = UserPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserProfileForm(request.POST, instance=request.user)
        pref_form = UserPreferenceForm(request.POST, instance=preference)
        if user_form.is_valid() and pref_form.is_valid():
            user_form.save()
            pref_obj = pref_form.save(commit=False)
            pref_obj.dark_mode = pref_obj.theme_mode == UserPreference.THEME_DARK
            pref_obj.save()
            return redirect("accounts:profile")
    else:
        user_form = UserProfileForm(instance=request.user)
        pref_form = UserPreferenceForm(instance=preference)

    context = {
        "user_form": user_form,
        "pref_form": pref_form,
    }
    return render(request, "accounts/profile.html", context)


def update_theme_preference_view(request: HttpRequest) -> JsonResponse:
    """
    Persist the user's selected theme_mode ('system', 'light', 'dark')
    into UserPreference when authenticated so DB and UI stay in sync.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    mode = request.POST.get("theme_mode", "").strip().lower()
    valid_modes = {
        UserPreference.THEME_SYSTEM,
        UserPreference.THEME_LIGHT,
        UserPreference.THEME_DARK,
    }
    if mode not in valid_modes:
        return JsonResponse({"error": "Invalid theme_mode"}, status=400)

    if request.user.is_authenticated:
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        pref.theme_mode = mode
        pref.dark_mode = mode == UserPreference.THEME_DARK
        pref.save(update_fields=["theme_mode", "dark_mode", "updated_at"])

    return JsonResponse({"status": "ok", "theme_mode": mode})
