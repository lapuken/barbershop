from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.audit.services import log_security_event
from apps.core.constants import Roles


def get_accessible_shops(user):
    from apps.shops.models import Shop

    if not user.is_authenticated:
        return Shop.objects.none()
    if user.role == Roles.PLATFORM_ADMIN:
        return Shop.objects.filter(is_active=True)
    return Shop.objects.filter(
        user_accesses__user=user, user_accesses__is_active=True, is_active=True
    ).distinct()


def get_shop_queryset_for_user(user):
    from apps.shops.models import Shop

    if not user.is_authenticated:
        return Shop.objects.none()
    if user.role == Roles.PLATFORM_ADMIN:
        return Shop.objects.all()
    return Shop.objects.filter(user_accesses__user=user, user_accesses__is_active=True).distinct()


def user_can_access_shop(user, shop) -> bool:
    if not user.is_authenticated:
        return False
    if user.role == Roles.PLATFORM_ADMIN:
        return True
    return user.shop_accesses.filter(shop=shop, is_active=True).exists()


def get_today_range():
    today = timezone.localdate()
    return today, today


def get_week_range():
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())
    return start, today


def get_month_range():
    today = timezone.localdate()
    start = today.replace(day=1)
    return start, today


def decimal_zero() -> Decimal:
    return Decimal("0.00")


def sum_amount(queryset, field: str):
    return queryset.aggregate(total=Coalesce(Sum(field), Decimal("0.00")))["total"]


def login_cache_key(identifier: str, ip_address: str) -> str:
    return f"login-attempts:{identifier}:{ip_address}"


def check_login_throttle(identifier: str, ip_address: str, limit: int, window_seconds: int) -> bool:
    key = login_cache_key(identifier, ip_address)
    attempts = cache.get(key, 0)
    return attempts >= limit


def record_login_failure(identifier: str, ip_address: str, limit: int, window_seconds: int) -> None:
    key = login_cache_key(identifier, ip_address)
    try:
        attempts = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        attempts = 1
    cache.touch(key, timeout=window_seconds)
    log_security_event(
        "login_failed",
        identifier=identifier,
        ip_address=ip_address,
        metadata={"attempts": attempts, "limit": limit},
    )


def reset_login_failures(identifier: str, ip_address: str) -> None:
    cache.delete(login_cache_key(identifier, ip_address))


def authenticate_and_login(request, username: str, password: str):
    identifier = username.strip().lower()
    ip_address = request.META.get("REMOTE_ADDR", "")
    from django.conf import settings

    if check_login_throttle(
        identifier, ip_address, settings.LOGIN_RATE_LIMIT, settings.LOGIN_RATE_WINDOW_SECONDS
    ):
        return None, "Too many failed login attempts. Try again later."

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        record_login_failure(
            identifier, ip_address, settings.LOGIN_RATE_LIMIT, settings.LOGIN_RATE_WINDOW_SECONDS
        )
        return None, "Invalid credentials."

    reset_login_failures(identifier, ip_address)
    login(request, user)
    log_security_event("login_success", actor=user, identifier=identifier, ip_address=ip_address)
    return user, None


def logout_user(request):
    if request.user.is_authenticated:
        log_security_event(
            "logout",
            actor=request.user,
            identifier=request.user.username,
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )
    logout(request)
