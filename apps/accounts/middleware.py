from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False) or not getattr(
            user, "must_change_password", False
        ):
            return self.get_response(request)

        if self._is_exempt_path(request.path):
            return self.get_response(request)

        if request.path.startswith("/api/"):
            return JsonResponse({"detail": "Password change required."}, status=403)

        password_change_url = reverse("accounts:password_change")
        query_string = urlencode({"next": request.get_full_path()})
        return redirect(f"{password_change_url}?{query_string}")

    def _is_exempt_path(self, path: str) -> bool:
        if settings.STATIC_URL and path.startswith(settings.STATIC_URL):
            return True
        if settings.MEDIA_URL and path.startswith(settings.MEDIA_URL):
            return True

        exempt_prefixes = (
            reverse("accounts:logout"),
            reverse("accounts:password_change"),
            reverse("accounts:password_reset"),
            "/accounts/reset/",
            reverse("admin:logout"),
        )
        return any(path.startswith(prefix) for prefix in exempt_prefixes)
