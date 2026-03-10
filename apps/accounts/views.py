from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordResetView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView

from apps.accounts.forms import AppPasswordChangeForm, LoginForm, ShopSelectorForm
from apps.audit.services import log_security_event
from apps.core.services import authenticate_and_login, logout_user


def get_safe_next_url(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if not next_url:
        return ""
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


class AppLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user, error = authenticate_and_login(
            self.request, form.cleaned_data["username"], form.cleaned_data["password"]
        )
        if error:
            form.add_error(None, error)
            return self.form_invalid(form)
        self.request.session["active_shop_id"] = None
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.request.user.is_authenticated and self.request.user.must_change_password:
            password_change_url = reverse("accounts:password_change")
            next_url = self.get_redirect_url()
            if next_url:
                return f"{password_change_url}?{urlencode({'next': next_url})}"
            return password_change_url
        return super().get_success_url()


class AppLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

    def post(self, request, *args, **kwargs):
        logout_user(request)
        return redirect(self.next_page)


class AppPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    success_url = reverse_lazy("accounts:login")


class AppPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change_form.html"
    form_class = AppPasswordChangeForm

    def form_valid(self, form):
        forced_change = bool(self.request.user.must_change_password)
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save(update_fields=["must_change_password"])
        messages.success(self.request, "Password updated.")
        log_security_event(
            "password_changed",
            actor=self.request.user,
            identifier=self.request.user.username,
            ip_address=self.request.META.get("REMOTE_ADDR", ""),
            metadata={"forced_change": forced_change},
        )
        return response

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url and next_url != reverse("accounts:password_change"):
            return next_url
        return str(reverse_lazy("core:dashboard"))


class ShopSelectorView(LoginRequiredMixin, FormView):
    template_name = "accounts/shop_selector.html"
    form_class = ShopSelectorForm
    success_url = reverse_lazy("core:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        shop = form.cleaned_data["shop"]
        self.request.session["active_shop_id"] = shop.id
        messages.success(self.request, f"Active shop switched to {shop.name}.")
        return super().form_valid(form)
