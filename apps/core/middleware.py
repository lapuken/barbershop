from __future__ import annotations

from apps.core.services import get_accessible_shops


class ActiveShopMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_shop = None
        if request.user.is_authenticated:
            shops = list(get_accessible_shops(request.user))
            selected_shop_id = request.session.get("active_shop_id")
            active_shop = next((shop for shop in shops if shop.id == selected_shop_id), None)
            if active_shop is None and shops:
                active_shop = shops[0]
                request.session["active_shop_id"] = active_shop.id
            request.active_shop = active_shop
        return self.get_response(request)
