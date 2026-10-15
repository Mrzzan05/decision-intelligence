from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
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
            pref_form.save()
            return redirect("accounts:profile")
    else:
        user_form = UserProfileForm(instance=request.user)
        pref_form = UserPreferenceForm(instance=preference)

    context = {
        "user_form": user_form,
        "pref_form": pref_form,
    }
    return render(request, "accounts/profile.html", context)
