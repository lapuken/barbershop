from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Count
from django.utils import timezone

from apps.appointments.models import Appointment, Customer
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.core.services import get_accessible_shops


def customer_queryset_for_user(user, shop=None):
    queryset = Customer.objects.select_related("shop")
    if user.role == Roles.PLATFORM_ADMIN:
        return queryset.filter(shop=shop) if shop else queryset
    shops = get_accessible_shops(user)
    queryset = queryset.filter(shop__in=shops)
    return queryset.filter(shop=shop) if shop else queryset


def appointment_queryset_for_user(user, shop=None):
    queryset = Appointment.objects.select_related(
        "shop",
        "customer",
        "barber",
        "created_by",
        "updated_by",
    )
    if user.role == Roles.PLATFORM_ADMIN:
        return queryset.filter(shop=shop) if shop else queryset
    shops = get_accessible_shops(user)
    queryset = queryset.filter(shop__in=shops)
    return queryset.filter(shop=shop) if shop else queryset


def dashboard_appointment_metrics(user, shop=None):
    today = timezone.localdate()
    queryset = appointment_queryset_for_user(user, shop=shop)
    today_appointments = queryset.filter(scheduled_start__date=today)
    status_counts = {
        row["status"]: row["total"]
        for row in (
            queryset.filter(scheduled_start__date=today)
            .values("status")
            .annotate(total=Count("id"))
        )
    }
    return {
        "today_total": today_appointments.count(),
        "today_confirmed": status_counts.get(Appointment.Status.CONFIRMED, 0),
        "today_requested": status_counts.get(Appointment.Status.REQUESTED, 0),
        "today_completed": status_counts.get(Appointment.Status.COMPLETED, 0),
    }


def upcoming_appointments_for_user(user, shop=None, limit=8):
    now = timezone.now()
    return list(
        appointment_queryset_for_user(user, shop=shop)
        .filter(
            scheduled_start__gte=now,
            status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED],
        )
        .order_by("scheduled_start")[:limit]
    )


def get_or_create_customer_for_booking(*, shop, customer_name, phone="", email="", notes=""):
    queryset = Customer.objects.filter(shop=shop)
    customer = None
    if phone:
        customer = queryset.filter(phone=phone).first()
    if customer is None and email:
        customer = queryset.filter(email__iexact=email).first()
    if customer is None:
        customer = Customer.objects.create(
            shop=shop,
            full_name=customer_name,
            phone=phone,
            email=email,
            notes=notes,
            is_active=True,
        )
    else:
        updates = []
        if phone and customer.phone != phone:
            customer.phone = phone
            updates.append("phone")
        if email and customer.email != email:
            customer.email = email
            updates.append("email")
        if notes and notes not in customer.notes:
            customer.notes = f"{customer.notes}\n{notes}".strip()
            updates.append("notes")
        if not customer.is_active:
            customer.is_active = True
            updates.append("is_active")
        if updates:
            updates.append("updated_at")
            customer.save(update_fields=updates)
    return customer


def create_public_booking(
    *,
    shop,
    customer_name,
    phone="",
    email="",
    barber=None,
    service_name,
    scheduled_start,
    duration_minutes,
    notes="",
):
    customer = get_or_create_customer_for_booking(
        shop=shop,
        customer_name=customer_name,
        phone=phone,
        email=email,
        notes=notes,
    )
    appointment = Appointment(
        shop=shop,
        customer=customer,
        barber=barber,
        service_name=service_name,
        scheduled_start=scheduled_start,
        duration_minutes=duration_minutes,
        status=Appointment.Status.REQUESTED,
        booking_source=Appointment.BookingSource.ONLINE,
        notes=notes,
    )
    appointment.full_clean()
    appointment.save()
    return appointment


def get_shop_timezone(shop):
    try:
        return ZoneInfo(shop.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def round_up_to_slot(aware_dt, *, slot_minutes=30):
    minute = aware_dt.minute
    remainder = minute % slot_minutes
    if remainder:
        aware_dt = aware_dt + timedelta(minutes=slot_minutes - remainder)
    return aware_dt.replace(second=0, microsecond=0)


def available_slots_for_shop(
    shop,
    *,
    days=7,
    per_barber_limit=6,
    duration_minutes=45,
    slot_minutes=30,
    open_hour=9,
    close_hour=18,
):
    tz = get_shop_timezone(shop)
    now_local = round_up_to_slot(timezone.now().astimezone(tz), slot_minutes=slot_minutes)
    barbers = list(Barber.objects.filter(shop=shop, is_active=True).order_by("full_name"))
    window_end = now_local + timedelta(days=days)
    appointments = (
        Appointment.objects.filter(
            shop=shop,
            barber__in=barbers,
            status__in=Appointment.ACTIVE_SCHEDULE_STATUSES,
            scheduled_start__lt=window_end,
        )
        .select_related("barber")
        .order_by("scheduled_start")
    )
    appointments_by_barber = {barber.id: [] for barber in barbers}
    for appointment in appointments:
        appointments_by_barber.setdefault(appointment.barber_id, []).append(appointment)

    results = []
    duration = timedelta(minutes=duration_minutes)
    for barber in barbers:
        slots = []
        current_day = now_local.date()
        for day_offset in range(days):
            day = current_day + timedelta(days=day_offset)
            slot = datetime.combine(day, dt_time(hour=open_hour), tzinfo=tz)
            end_of_day = datetime.combine(day, dt_time(hour=close_hour), tzinfo=tz)
            if day_offset == 0 and slot < now_local:
                slot = round_up_to_slot(now_local, slot_minutes=slot_minutes)
            while slot + duration <= end_of_day:
                overlaps = False
                for appointment in appointments_by_barber.get(barber.id, []):
                    appointment_end = appointment.scheduled_start + timedelta(
                        minutes=appointment.duration_minutes
                    )
                    if appointment.scheduled_start < slot + duration and appointment_end > slot:
                        overlaps = True
                        break
                if not overlaps:
                    slots.append(slot)
                    if len(slots) >= per_barber_limit:
                        break
                slot += timedelta(minutes=slot_minutes)
            if len(slots) >= per_barber_limit:
                break
        results.append({"barber": barber, "slots": slots})
    return results
