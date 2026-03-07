from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.constants import Roles
from apps.core.permissions import SalesRolePermission
from apps.core.services import get_accessible_shops, user_can_access_shop
from apps.expenses.models import Expense
from apps.expenses.serializers import ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [SalesRolePermission]

    def get_queryset(self):
        queryset = Expense.objects.select_related("shop", "created_by", "updated_by")
        if self.request.user.role == Roles.PLATFORM_ADMIN:
            return queryset
        return queryset.filter(shop__in=get_accessible_shops(self.request.user))

    def perform_create(self, serializer):
        shop = serializer.validated_data["shop"]
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot create expenses for this shop.")
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        shop = serializer.validated_data.get("shop", serializer.instance.shop)
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot modify expenses for this shop.")
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in Roles.MANAGEMENT and request.user.role != Roles.PLATFORM_ADMIN:
            return Response(
                {"detail": "You do not have permission to delete expenses."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
