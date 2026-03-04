from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment, Customer
from apps.appointments.serializers import (
    AppointmentSerializer,
    CustomerSerializer,
    PublicBookingSerializer,
)
from apps.appointments.services import available_slots_for_shop, create_public_booking
from apps.core.constants import Roles
from apps.core.permissions import SalesRolePermission
from apps.core.services import get_accessible_shops, user_can_access_shop
from apps.shops.models import Shop


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [SalesRolePermission]

    def get_queryset(self):
        queryset = Customer.objects.select_related("shop")
        if self.request.user.role == Roles.PLATFORM_ADMIN:
            return queryset
        return queryset.filter(shop__in=get_accessible_shops(self.request.user))

    def perform_create(self, serializer):
        shop = serializer.validated_data["shop"]
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot create customers for this shop.")
        serializer.save()

    def perform_update(self, serializer):
        shop = serializer.validated_data.get("shop", serializer.instance.shop)
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot modify customers for this shop.")
        serializer.save()

    def perform_destroy(self, instance):
        instance.soft_delete(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in Roles.MANAGEMENT and request.user.role != Roles.PLATFORM_ADMIN:
            return Response(
                {"detail": "You do not have permission to delete customers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [SalesRolePermission]

    def get_queryset(self):
        queryset = Appointment.objects.select_related(
            "shop",
            "customer",
            "barber",
            "created_by",
            "updated_by",
        )
        if self.request.user.role == Roles.PLATFORM_ADMIN:
            return queryset
        return queryset.filter(shop__in=get_accessible_shops(self.request.user))

    def perform_create(self, serializer):
        shop = serializer.validated_data["shop"]
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot create appointments for this shop.")
        serializer.save()

    def perform_update(self, serializer):
        shop = serializer.validated_data.get("shop", serializer.instance.shop)
        if not user_can_access_shop(self.request.user, shop):
            raise PermissionDenied("You cannot modify appointments for this shop.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in Roles.MANAGEMENT and request.user.role != Roles.PLATFORM_ADMIN:
            return Response(
                {"detail": "You do not have permission to delete appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicBookingAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PublicBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = create_public_booking(
            shop=serializer.validated_data["shop"],
            customer_name=serializer.validated_data["customer_name"],
            phone=serializer.validated_data.get("phone", ""),
            email=serializer.validated_data.get("email", ""),
            telegram_chat_id=serializer.validated_data.get("telegram_chat_id", ""),
            preferred_confirmation_channel=serializer.validated_data.get(
                "preferred_confirmation_channel"
            ),
            barber=serializer.validated_data.get("barber"),
            service_name=serializer.validated_data["service_name"],
            scheduled_start=serializer.validated_data["scheduled_start"],
            duration_minutes=serializer.validated_data["duration_minutes"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            {
                "id": appointment.id,
                "status": appointment.status,
                "message": "Booking request submitted.",
            },
            status=status.HTTP_201_CREATED,
        )


class PublicAvailabilityAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        shop_id = request.GET.get("shop", "").strip()
        selected_shop = Shop.objects.filter(pk=shop_id, is_active=True).first()
        if selected_shop is None:
            return Response({"detail": "Valid shop query parameter is required."}, status=400)
        availability_groups = available_slots_for_shop(selected_shop)
        return Response(
            {
                "shop": selected_shop.name,
                "availability": [
                    {
                        "barber": group["barber"].full_name,
                        "slots": [slot.isoformat() for slot in group["slots"]],
                    }
                    for group in availability_groups
                ],
            }
        )
