from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentNotification, Customer
from apps.appointments.sharing import (
    build_booking_confirmation_message,
    normalize_whatsapp_number,
)


@dataclass
class NotificationResult:
    attempted: bool
    sent: bool
    status: str
    channel: str = ""
    reason: str = ""
    log_id: int | None = None

    @property
    def channel_label(self) -> str:
        if self.channel == AppointmentNotification.Channel.WHATSAPP:
            return "WhatsApp"
        if self.channel == AppointmentNotification.Channel.TELEGRAM:
            return "Telegram"
        return "notification"


class NotificationDeliveryError(Exception):
    def __init__(self, message: str, response_json: dict | None = None):
        super().__init__(message)
        self.response_json = response_json or {}


def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.APPOINTMENT_NOTIFICATION_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        response_json = {}
        if body:
            try:
                response_json = json.loads(body)
            except json.JSONDecodeError:
                response_json = {"raw": body}
        raise NotificationDeliveryError(
            f"Provider returned HTTP {exc.code}.",
            response_json=response_json,
        ) from exc
    except URLError as exc:
        raise NotificationDeliveryError(str(exc)) from exc


def build_public_availability_url(request, shop) -> str:
    path = f"{reverse('appointments:public-availability')}?shop={shop.id}"
    if request is None:
        return path
    return request.build_absolute_uri(path)


def _notification_candidates(customer: Customer) -> list[str]:
    preferred = customer.preferred_confirmation_channel
    if preferred == Customer.ConfirmationChannel.WHATSAPP:
        return [
            AppointmentNotification.Channel.WHATSAPP,
            AppointmentNotification.Channel.TELEGRAM,
        ]
    if preferred == Customer.ConfirmationChannel.TELEGRAM:
        return [
            AppointmentNotification.Channel.TELEGRAM,
            AppointmentNotification.Channel.WHATSAPP,
        ]
    return [
        AppointmentNotification.Channel.WHATSAPP,
        AppointmentNotification.Channel.TELEGRAM,
    ]


def _whatsapp_ready(customer: Customer) -> bool:
    return bool(
        normalize_whatsapp_number(customer.phone)
        and settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_PHONE_NUMBER_ID
    )


def _telegram_ready(customer: Customer) -> bool:
    return bool(customer.telegram_chat_id and settings.TELEGRAM_BOT_TOKEN)


def _build_skip_reason(customer: Customer) -> str:
    missing = []
    if not normalize_whatsapp_number(customer.phone):
        missing.append("customer WhatsApp number")
    if not customer.telegram_chat_id:
        missing.append("customer Telegram chat ID")
    if not settings.WHATSAPP_ACCESS_TOKEN:
        missing.append("WHATSAPP_ACCESS_TOKEN")
    if not settings.WHATSAPP_PHONE_NUMBER_ID:
        missing.append("WHATSAPP_PHONE_NUMBER_ID")
    if not settings.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not missing:
        return "No delivery route was available for this customer."
    return "Missing delivery prerequisites: " + ", ".join(missing) + "."


def _create_notification_log(
    *,
    appointment: Appointment,
    status: str,
    event_type: str,
    channel: str = "",
    recipient: str = "",
    provider_response_json: dict | None = None,
    provider_message_id: str = "",
    error_message: str = "",
    sent: bool = False,
) -> AppointmentNotification:
    return AppointmentNotification.objects.create(
        appointment=appointment,
        customer=appointment.customer,
        shop=appointment.shop,
        channel=channel,
        event_type=event_type,
        status=status,
        recipient=recipient,
        provider_response_json=provider_response_json or {},
        provider_message_id=provider_message_id,
        error_message=error_message,
        sent_at=timezone.now() if sent else None,
    )


def _send_whatsapp_confirmation(appointment: Appointment, message: str) -> NotificationResult:
    recipient = normalize_whatsapp_number(appointment.customer.phone)
    url = (
        f"{settings.WHATSAPP_API_BASE_URL.rstrip('/')}/"
        f"{settings.WHATSAPP_API_VERSION.strip('/')}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message,
        },
    }
    response_json = _post_json(
        url,
        payload,
        headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
    )
    provider_message_id = ""
    messages = response_json.get("messages") or []
    if messages:
        provider_message_id = messages[0].get("id", "")
    log = _create_notification_log(
        appointment=appointment,
        status=AppointmentNotification.Status.SENT,
        event_type=AppointmentNotification.EventType.BOOKING_CONFIRMED,
        channel=AppointmentNotification.Channel.WHATSAPP,
        recipient=recipient,
        provider_response_json=response_json,
        provider_message_id=provider_message_id,
        sent=True,
    )
    return NotificationResult(
        attempted=True,
        sent=True,
        status=AppointmentNotification.Status.SENT,
        channel=AppointmentNotification.Channel.WHATSAPP,
        log_id=log.id,
    )


def _send_telegram_confirmation(appointment: Appointment, message: str) -> NotificationResult:
    recipient = appointment.customer.telegram_chat_id
    url = (
        f"{settings.TELEGRAM_API_BASE_URL.rstrip('/')}/"
        f"bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    )
    payload = {
        "chat_id": recipient,
        "text": message,
        "disable_web_page_preview": True,
    }
    response_json = _post_json(url, payload)
    provider_message_id = ""
    if response_json.get("ok") and response_json.get("result"):
        provider_message_id = str(response_json["result"].get("message_id", ""))
    log = _create_notification_log(
        appointment=appointment,
        status=AppointmentNotification.Status.SENT,
        event_type=AppointmentNotification.EventType.BOOKING_CONFIRMED,
        channel=AppointmentNotification.Channel.TELEGRAM,
        recipient=recipient,
        provider_response_json=response_json,
        provider_message_id=provider_message_id,
        sent=True,
    )
    return NotificationResult(
        attempted=True,
        sent=True,
        status=AppointmentNotification.Status.SENT,
        channel=AppointmentNotification.Channel.TELEGRAM,
        log_id=log.id,
    )


def send_booking_confirmation(appointment: Appointment, *, request=None) -> NotificationResult:
    if appointment.status != Appointment.Status.CONFIRMED:
        return NotificationResult(
            attempted=False,
            sent=False,
            status=AppointmentNotification.Status.SKIPPED,
            reason="Appointment is not confirmed.",
        )

    availability_url = build_public_availability_url(request, appointment.shop)
    message = build_booking_confirmation_message(appointment, availability_url)
    customer = appointment.customer

    for channel in _notification_candidates(customer):
        try:
            if channel == AppointmentNotification.Channel.WHATSAPP and _whatsapp_ready(customer):
                return _send_whatsapp_confirmation(appointment, message)
            if channel == AppointmentNotification.Channel.TELEGRAM and _telegram_ready(customer):
                return _send_telegram_confirmation(appointment, message)
        except NotificationDeliveryError as exc:
            log = _create_notification_log(
                appointment=appointment,
                status=AppointmentNotification.Status.FAILED,
                event_type=AppointmentNotification.EventType.BOOKING_CONFIRMED,
                channel=channel,
                recipient=(
                    normalize_whatsapp_number(customer.phone)
                    if channel == AppointmentNotification.Channel.WHATSAPP
                    else customer.telegram_chat_id
                ),
                provider_response_json=exc.response_json,
                error_message=str(exc),
            )
            return NotificationResult(
                attempted=True,
                sent=False,
                status=AppointmentNotification.Status.FAILED,
                channel=channel,
                reason=str(exc),
                log_id=log.id,
            )

    reason = _build_skip_reason(customer)
    log = _create_notification_log(
        appointment=appointment,
        status=AppointmentNotification.Status.SKIPPED,
        event_type=AppointmentNotification.EventType.BOOKING_CONFIRMED,
        channel=customer.preferred_confirmation_channel
        if customer.preferred_confirmation_channel != Customer.ConfirmationChannel.AUTO
        else "",
        error_message=reason,
    )
    return NotificationResult(
        attempted=False,
        sent=False,
        status=AppointmentNotification.Status.SKIPPED,
        channel=(
            customer.preferred_confirmation_channel
            if customer.preferred_confirmation_channel != Customer.ConfirmationChannel.AUTO
            else ""
        ),
        reason=reason,
        log_id=log.id,
    )
