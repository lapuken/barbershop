from __future__ import annotations

from urllib.parse import quote


def normalize_whatsapp_number(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def normalize_telegram_handle(handle: str) -> str:
    return handle.strip().lstrip("@")


def build_whatsapp_url(phone: str, text: str) -> str:
    normalized = normalize_whatsapp_number(phone)
    if not normalized:
        return ""
    return f"https://wa.me/{normalized}?text={quote(text)}"


def build_telegram_share_url(text: str, url: str = "") -> str:
    share_url = "https://t.me/share/url?"
    if url:
        return f"{share_url}url={quote(url)}&text={quote(text)}"
    return f"{share_url}text={quote(text)}"


def build_telegram_direct_url(handle: str, text: str) -> str:
    normalized = normalize_telegram_handle(handle)
    if not normalized:
        return ""
    return f"https://t.me/{normalized}?text={quote(text)}"


def build_availability_message(shop, availability_groups, availability_url: str) -> str:
    lines = [f"{shop.name} current availability:"]
    for group in availability_groups:
        if not group["slots"]:
            continue
        slots = ", ".join(slot.strftime("%b %d %I:%M %p") for slot in group["slots"][:3])
        lines.append(f"{group['barber'].full_name}: {slots}")
    lines.append(f"Full schedule: {availability_url}")
    lines.append("Reply with your preferred time to confirm.")
    return "\n".join(lines)


def build_appointment_message(appointment, availability_url: str) -> str:
    message_lines = [
        f"Appointment update from {appointment.shop.name}",
        f"Service: {appointment.service_name}",
        f"When: {appointment.scheduled_start.strftime('%b %d %I:%M %p')}",
        f"Status: {appointment.get_status_display()}",
    ]
    if appointment.barber:
        message_lines.append(f"Barber: {appointment.barber.full_name}")
    message_lines.append(f"Availability and reschedule options: {availability_url}")
    return "\n".join(message_lines)


def build_shop_contact_message(shop, booking_url: str, availability_url: str) -> str:
    return "\n".join(
        [
            f"Hello {shop.name},",
            "I would like to schedule an appointment.",
            f"Booking page: {booking_url}",
            f"Available times: {availability_url}",
        ]
    )

