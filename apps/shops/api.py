from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.core.constants import Roles
from apps.shops.models import Shop
from apps.shops.serializers import ShopSerializer


class ShopViewSet(viewsets.ModelViewSet):
    serializer_class = ShopSerializer
    queryset = Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == Roles.PLATFORM_ADMIN:
            return Shop.objects.all()
        return Shop.objects.filter(user_accesses__user=user, user_accesses__is_active=True).distinct()

    def create(self, request, *args, **kwargs):
        if request.user.role != Roles.PLATFORM_ADMIN:
            raise PermissionDenied("Only platform admins can create shops.")
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != Roles.PLATFORM_ADMIN:
            raise PermissionDenied("Only platform admins can modify shops.")
        return super().partial_update(request, *args, **kwargs)
