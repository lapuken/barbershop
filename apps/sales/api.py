from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.constants import Roles
from apps.core.permissions import SalesRolePermission
from apps.core.services import get_accessible_shops, user_can_access_shop
from apps.sales.models import Sale
from apps.sales.serializers import SaleSerializer


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [SalesRolePermission]

    def get_queryset(self):
        queryset = Sale.objects.select_related(
            "shop", "barber", "created_by", "updated_by"
        ).prefetch_related("items")
        if self.request.user.role == Roles.PLATFORM_ADMIN:
            return queryset
        return queryset.filter(shop__in=get_accessible_shops(self.request.user))

    def perform_create(self, serializer):
        shop = serializer.validated_data["shop"]
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot create sales for this shop.")
        serializer.save()

    def perform_update(self, serializer):
        shop = serializer.validated_data.get("shop", serializer.instance.shop)
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot modify sales for this shop.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in Roles.MANAGEMENT and request.user.role != Roles.PLATFORM_ADMIN:
            return Response(
                {"detail": "You do not have permission to delete sales."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
