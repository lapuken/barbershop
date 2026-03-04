from apps.core.services import get_accessible_shops


def current_shop(request):
    if not request.user.is_authenticated:
        return {"current_shop": None, "accessible_shops": []}

    return {
        "current_shop": getattr(request, "active_shop", None),
        "accessible_shops": get_accessible_shops(request.user),
    }
