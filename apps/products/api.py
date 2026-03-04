from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.constants import Roles
from apps.core.permissions import ManagementRolePermission
from apps.core.services import get_accessible_shops, user_can_access_shop
from apps.products.models import Product
from apps.products.serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [ManagementRolePermission]

    def get_queryset(self):
        queryset = Product.objects.select_related("shop")
        if self.request.user.role == Roles.PLATFORM_ADMIN:
            return queryset
        return queryset.filter(shop__in=get_accessible_shops(self.request.user))

    def perform_create(self, serializer):
        shop = serializer.validated_data["shop"]
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot create products for this shop.")
        serializer.save()

    def perform_update(self, serializer):
        shop = serializer.validated_data.get("shop", serializer.instance.shop)
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot modify products for this shop.")
        serializer.save()

    def perform_destroy(self, instance):
        instance.soft_delete(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
