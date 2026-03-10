#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from simple_pdf import (
    PDFBuilder,
    char_capacity,
    line_command,
    rectangle_command,
    stream_object,
    text_command,
)

PAGE_WIDTH = 792
PAGE_HEIGHT = 612
MARGIN = 36
FONT_SIZE = 10
SMALL_FONT_SIZE = 8
TITLE_FONT_SIZE = 16
SUBTITLE_FONT_SIZE = 9
LINE_HEIGHT = 12
CELL_PADDING = 4


@dataclass(frozen=True)
class RoleDefinition:
    code: str
    label: str
    capability_summary: str


ROLE_DEFINITIONS = [
    RoleDefinition(
        code="platform_admin",
        label="Platform Admin",
        capability_summary=(
            "All-shop oversight. Can create and edit shops and has full create, edit, "
            "and archive access for barbers, products, customers, appointments, sales, "
            "and expenses, plus full reports, audit, settings, and API access."
        ),
    ),
    RoleDefinition(
        code="shop_owner",
        label="Shop Owner",
        capability_summary=(
            "Assigned-shop management role. Full operational create, edit, and archive "
            "access for barbers, products, customers, appointments, sales, and expenses "
            "inside assigned shops. Cannot create or edit shops or access unassigned shops."
        ),
    ),
    RoleDefinition(
        code="shop_manager",
        label="Shop Manager",
        capability_summary=(
            "Currently the same application permissions as Shop Owner: full operational "
            "create, edit, and archive access inside assigned shops. Cannot create or edit "
            "shops or access unassigned shops."
        ),
    ),
    RoleDefinition(
        code="cashier",
        label="Cashier / Front Desk",
        capability_summary=(
            "Assigned-shop front-desk role. Can view operational lists and create or edit "
            "customers, appointments, sales, and expenses. Cannot manage shops, barbers, "
            "or products, and cannot archive business records."
        ),
    ),
    RoleDefinition(
        code="barber",
        label="Barber",
        capability_summary=(
            "Assigned-shop read-only operational visibility in the web UI. Can access the "
            "dashboard, reports, audit log, settings, and list pages, but cannot create, "
            "edit, archive, or use operational write APIs."
        ),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a PDF summary of application roles, current assignments, and capabilities."
    )
    parser.add_argument(
        "--input", required=True, help="Path to the queried role-assignment JSON file."
    )
    parser.add_argument("--output", required=True, help="Path to the PDF file to create.")
    parser.add_argument(
        "--generated-on",
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        help="Timestamp to print in the report header.",
    )
    return parser.parse_args()


def load_users(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def group_users_by_role(users: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for user in users:
        grouped.setdefault(user["role"], []).append(user)
    for role_users in grouped.values():
        role_users.sort(key=lambda item: item["username"].lower())
    return grouped


def describe_user(user: dict) -> str:
    email = f" <{user['email']}>" if user.get("email") else ""
    active_shops = [shop["name"] for shop in user.get("shops", []) if shop.get("is_active")]
    inactive_shops = [shop["name"] for shop in user.get("shops", []) if not shop.get("is_active")]

    if user["role"] == "platform_admin":
        scope = "all shops"
    elif active_shops:
        scope = ", ".join(active_shops)
    elif inactive_shops:
        scope = "inactive shop access: " + ", ".join(inactive_shops)
    else:
        scope = "no shop access"

    status = ""
    if not user.get("is_active", True):
        status = " [inactive]"

    return f"{user['username']}{email} ({scope}){status}"


def build_rows(users: list[dict]) -> list[dict[str, str]]:
    grouped = group_users_by_role(users)
    rows = []
    for role in ROLE_DEFINITIONS:
        role_users = grouped.get(role.code, [])
        current_users = (
            "\n".join(describe_user(user) for user in role_users) if role_users else "None assigned"
        )
        rows.append(
            {
                "role": f"{role.label}\n({role.code})",
                "current_users": current_users,
                "capabilities": role.capability_summary,
            }
        )
    return rows


def wrap_text(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        return [text]

    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                paragraph,
                width=max_chars,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [""]
        )
    return lines or [""]


def render_pages(rows: list[dict[str, str]], generated_on: str) -> list[str]:
    columns = [
        ("role", 130),
        ("current_users", 250),
        ("capabilities", 340),
    ]
    total_width = sum(width for _key, width in columns)
    x_positions = [MARGIN]
    for _key, width in columns[:-1]:
        x_positions.append(x_positions[-1] + width)

    pages: list[list[str]] = []
    page_commands: list[str] = []

    def start_page(page_number: int) -> tuple[list[str], float]:
        commands: list[str] = ["0.4 w"]
        title_y = PAGE_HEIGHT - MARGIN
        commands.append(
            text_command(
                "Smart Barber Shops Role Summary", MARGIN, title_y, font="F2", size=TITLE_FONT_SIZE
            )
        )
        commands.append(
            text_command(
                f"Generated: {generated_on} | Page {page_number}",
                MARGIN,
                title_y - 18,
                size=SUBTITLE_FONT_SIZE,
            )
        )
        commands.append(
            text_command(
                "Capabilities are based on USER_ROLES.md and the enforced role gates in the Django app.",
                MARGIN,
                title_y - 32,
                size=SUBTITLE_FONT_SIZE,
            )
        )

        header_top = title_y - 52
        header_height = 24
        header_bottom = header_top - header_height
        commands.append(rectangle_command(MARGIN, header_bottom, total_width, header_height))

        header_labels = [
            "Role",
            "Current users with this role",
            "Capabilities",
        ]
        for index, label in enumerate(header_labels):
            x = x_positions[index] + CELL_PADDING
            y = header_top - 16
            commands.append(text_command(label, x, y, font="F2", size=FONT_SIZE))

        for x in x_positions[1:]:
            commands.append(line_command(x, header_top, x, header_bottom))

        return commands, header_bottom

    page_number = 1
    page_commands, current_y = start_page(page_number)

    for row in rows:
        wrapped_columns: list[list[str]] = []
        max_lines = 1
        for key, width in columns:
            wrapped = wrap_text(row[key], char_capacity(width))
            wrapped_columns.append(wrapped)
            max_lines = max(max_lines, len(wrapped))

        row_height = (max_lines * LINE_HEIGHT) + (CELL_PADDING * 2)
        row_bottom = current_y - row_height

        if row_bottom < MARGIN + 20:
            pages.append(page_commands)
            page_number += 1
            page_commands, current_y = start_page(page_number)
            row_bottom = current_y - row_height

        page_commands.append(rectangle_command(MARGIN, row_bottom, total_width, row_height))
        for x in x_positions[1:]:
            page_commands.append(line_command(x, current_y, x, row_bottom))

        for column_index, wrapped in enumerate(wrapped_columns):
            text_x = x_positions[column_index] + CELL_PADDING
            text_y = current_y - CELL_PADDING - FONT_SIZE
            font_name = "F2" if column_index == 0 else "F1"
            for line in wrapped:
                page_commands.append(
                    text_command(line, text_x, text_y, font=font_name, size=FONT_SIZE)
                )
                text_y -= LINE_HEIGHT

        current_y = row_bottom

    pages.append(page_commands)
    return ["\n".join(commands) for commands in pages]


def write_pdf(output_path: Path, pages: list[str]) -> None:
    builder = PDFBuilder()
    regular_font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    bold_font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>")

    content_ids = [builder.add_object(stream_object(page)) for page in pages]
    pages_id = builder.reserve_object_id()
    page_ids = []

    for content_id in content_ids:
        page_payload = (
            f"<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {regular_font_id} 0 R /F2 {bold_font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_ids.append(builder.add_object(page_payload))

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    builder.add_object(
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>",
        object_id=pages_id,
    )
    catalog_id = builder.add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(builder.build(catalog_id))


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    rows = build_rows(load_users(input_path))
    pages = render_pages(rows, args.generated_on)
    write_pdf(output_path, pages)


if __name__ == "__main__":
    main()
