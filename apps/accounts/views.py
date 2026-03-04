from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.accounts.forms import LoginForm, ShopSelectorForm
from apps.core.services import authenticate_and_login, logout_user


class AppLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user, error = authenticate_and_login(self.request, form.cleaned_data["username"], form.cleaned_data["password"])
        if error:
            form.add_error(None, error)
            return self.form_invalid(form)
        self.request.session["active_shop_id"] = None
        return redirect(self.get_success_url())


class AppLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

    def post(self, request, *args, **kwargs):
        logout_user(request)
        return redirect(self.next_page)


class AppPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    success_url = reverse_lazy("accounts:login")


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
