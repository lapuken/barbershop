#!/usr/bin/env python3
from __future__ import annotations

import argparse
import textwrap
from dataclasses import dataclass, field
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

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 48
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
TITLE_FONT_SIZE = 18
SECTION_FONT_SIZE = 13
BODY_FONT_SIZE = 10
CODE_FONT_SIZE = 9
BODY_LINE_HEIGHT = 13
CODE_LINE_HEIGHT = 11
RULE_Y_OFFSET = 32


@dataclass(frozen=True)
class RoleProvisioningGuide:
    label: str
    code: str
    purpose: str
    json_path: str
    is_staff: bool
    is_superuser: bool
    shop_access_required: bool
    initializer_steps: list[str]
    json_example: list[str]
    admin_steps: list[str]
    notes: list[str] = field(default_factory=list)


GENERAL_RULES = [
    "There are two supported provisioning paths today: the JSON-driven go-live initializer for controlled batches, and Django admin for one-off additions later.",
    "platform_admin users do not get UserShopAccess rows.",
    "Every non-platform_admin user must have at least one active UserShopAccess row.",
    "Only platform_admin should have is_superuser set to true.",
    "Set a strong temporary password and must_change_password = true for normal human users.",
    "Barber login accounts are separate from Barber business records used by scheduling and operational flows.",
]


ROLE_GUIDES = [
    RoleProvisioningGuide(
        label="Platform Admin",
        code="platform_admin",
        purpose="System-wide administrator who can work across all shops.",
        json_path="platform_admin",
        is_staff=True,
        is_superuser=True,
        shop_access_required=False,
        initializer_steps=[
            "Add or update the top-level platform_admin object in golive-init.json.",
            "Set username, email, password, and optional phone.",
            "Use must_change_password: true for a real human admin account.",
            "Run ./scripts/initialize-golive.sh /path/to/golive-init.json.",
            "Do not add a UserShopAccess entry for this user.",
        ],
        json_example=[
            '"platform_admin": {',
            '  "username": "platformadmin",',
            '  "email": "admin@example.com",',
            '  "password": "TemporaryAdminPass123!",',
            '  "phone": "+265-999-000-001",',
            '  "must_change_password": true',
            "}",
        ],
        admin_steps=[
            "Open /admin/ and create a new User.",
            "Set username, email, role = platform_admin, and a strong temporary password.",
            "Set is_active = true, is_staff = true, and is_superuser = true.",
            "Set must_change_password = true.",
            "Save the user.",
            "Do not create a UserShopAccess row for this user.",
        ],
    ),
    RoleProvisioningGuide(
        label="Shop Owner",
        code="shop_owner",
        purpose="Branch owner with full operational control inside assigned shops.",
        json_path="shops[].users[]",
        is_staff=True,
        is_superuser=False,
        shop_access_required=True,
        initializer_steps=[
            "Add the user under the correct shop's shops[].users[] list.",
            'Set "role": "shop_owner".',
            "Set username, email, password, and optional phone.",
            "Leave shop_access_is_active as true unless you intentionally want inactive access.",
            "Run ./scripts/initialize-golive.sh /path/to/golive-init.json.",
        ],
        json_example=[
            "{",
            '  "username": "owner-downtown",',
            '  "email": "owner@example.com",',
            '  "password": "TemporaryOwnerPass123!",',
            '  "role": "shop_owner",',
            '  "phone": "+265-999-000-010",',
            '  "must_change_password": true',
            "}",
        ],
        admin_steps=[
            "Open /admin/ and create a new User.",
            "Set role = shop_owner.",
            "Set is_active = true, is_staff = true, and is_superuser = false.",
            "Set a strong temporary password and must_change_password = true.",
            "Save the user.",
            "Create one or more UserShopAccess rows for the shops this owner should access.",
            "Set each UserShopAccess.is_active = true.",
        ],
    ),
    RoleProvisioningGuide(
        label="Shop Manager",
        code="shop_manager",
        purpose="Daily operations manager. In the current app, this role has the same permissions as shop_owner.",
        json_path="shops[].users[]",
        is_staff=True,
        is_superuser=False,
        shop_access_required=True,
        initializer_steps=[
            "Add the user under the correct shop's shops[].users[] list.",
            'Set "role": "shop_manager".',
            "Set username, email, password, and optional phone.",
            "Keep shop_access_is_active set to true unless you need disabled access.",
            "Run ./scripts/initialize-golive.sh /path/to/golive-init.json.",
        ],
        json_example=[
            "{",
            '  "username": "manager-downtown",',
            '  "email": "manager@example.com",',
            '  "password": "TemporaryManagerPass123!",',
            '  "role": "shop_manager",',
            '  "phone": "+265-999-000-011",',
            '  "must_change_password": true',
            "}",
        ],
        admin_steps=[
            "Open /admin/ and create a new User.",
            "Set role = shop_manager.",
            "Set is_active = true, is_staff = true, and is_superuser = false.",
            "Set a strong temporary password and must_change_password = true.",
            "Save the user.",
            "Create one or more active UserShopAccess rows for the shops this manager should use.",
        ],
    ),
    RoleProvisioningGuide(
        label="Cashier / Front Desk",
        code="cashier",
        purpose="Front-desk staff who handle appointments, sales, customers, and expense entry.",
        json_path="shops[].users[]",
        is_staff=False,
        is_superuser=False,
        shop_access_required=True,
        initializer_steps=[
            "Add the user under the correct shop's shops[].users[] list.",
            'Set "role": "cashier".',
            "Set username, email, password, and optional phone.",
            "Keep shop_access_is_active set to true unless you intentionally want inactive access.",
            "Run ./scripts/initialize-golive.sh /path/to/golive-init.json.",
        ],
        json_example=[
            "{",
            '  "username": "cashier-downtown",',
            '  "email": "cashier@example.com",',
            '  "password": "TemporaryCashierPass123!",',
            '  "role": "cashier",',
            '  "phone": "+265-999-000-012",',
            '  "must_change_password": true',
            "}",
        ],
        admin_steps=[
            "Open /admin/ and create a new User.",
            "Set role = cashier.",
            "Set is_active = true, is_staff = false, and is_superuser = false.",
            "Set a strong temporary password and must_change_password = true.",
            "Save the user.",
            "Create one or more active UserShopAccess rows for the shops this cashier should use.",
        ],
    ),
    RoleProvisioningGuide(
        label="Barber",
        code="barber",
        purpose="Read-only operational user who needs sign-in access inside assigned shops.",
        json_path="shops[].users[]",
        is_staff=False,
        is_superuser=False,
        shop_access_required=True,
        initializer_steps=[
            "Add the login account under the correct shop's shops[].users[] list.",
            'Set "role": "barber".',
            "Set username, email, password, and optional phone.",
            "Keep shop_access_is_active set to true unless you intentionally want inactive access.",
            "Run ./scripts/initialize-golive.sh /path/to/golive-init.json.",
        ],
        json_example=[
            "{",
            '  "username": "barber-downtown",',
            '  "email": "barber@example.com",',
            '  "password": "TemporaryBarberPass123!",',
            '  "role": "barber",',
            '  "phone": "+265-999-000-013",',
            '  "must_change_password": true',
            "}",
        ],
        admin_steps=[
            "Open /admin/ and create a new User.",
            "Set role = barber.",
            "Set is_active = true, is_staff = false, and is_superuser = false.",
            "Set a strong temporary password and must_change_password = true.",
            "Save the user.",
            "Create one or more active UserShopAccess rows for the shops this barber should access.",
        ],
        notes=[
            "If the person should appear in barber lists, appointment booking, or sale attribution, also create or update the matching Barber business record for that shop.",
        ],
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a PDF guide for provisioning Smart Barber Shops roles."
    )
    parser.add_argument("--output", required=True, help="Path to the PDF file to create.")
    parser.add_argument(
        "--generated-on",
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        help="Timestamp to print in the report header.",
    )
    return parser.parse_args()


def wrap_prefixed(text: str, width: int, prefix: str = "", continuation: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=width,
        initial_indent=prefix,
        subsequent_indent=continuation,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [prefix.rstrip()]


class ProvisioningGuideRenderer:
    def __init__(self, generated_on: str) -> None:
        self.generated_on = generated_on
        self.pages: list[str] = []
        self.page_number = 0
        self.commands: list[str] = []
        self.current_y = 0.0
        self.new_page()

    def new_page(self) -> None:
        if self.commands:
            self.pages.append("\n".join(self.commands))

        self.page_number += 1
        self.commands = ["0.4 w"]
        title_y = PAGE_HEIGHT - MARGIN
        self.commands.append(
            text_command(
                "Smart Barber Shops Role Provisioning Guide",
                MARGIN,
                title_y,
                font="F2",
                size=TITLE_FONT_SIZE,
            )
        )
        self.commands.append(
            text_command(
                f"Generated: {self.generated_on} | Page {self.page_number}",
                MARGIN,
                title_y - 18,
                size=9,
            )
        )
        self.commands.append(
            text_command(
                "Based on USER_ROLES.md and the supported provisioning paths in the repository.",
                MARGIN,
                title_y - 32,
                size=9,
            )
        )
        self.commands.append(
            line_command(
                MARGIN, title_y - RULE_Y_OFFSET, PAGE_WIDTH - MARGIN, title_y - RULE_Y_OFFSET
            )
        )
        self.current_y = title_y - 50

    def finish(self) -> list[str]:
        if self.commands:
            self.pages.append("\n".join(self.commands))
            self.commands = []
        return self.pages

    def ensure_space(self, height: float) -> None:
        if self.current_y - height < MARGIN:
            self.new_page()

    def add_heading(
        self,
        text: str,
        *,
        size: int = SECTION_FONT_SIZE,
        before: int = 10,
        after: int = 6,
        keep_with_next: int = 0,
    ) -> None:
        self.ensure_space(before + size + after + keep_with_next)
        self.current_y -= before
        self.commands.append(text_command(text, MARGIN, self.current_y, font="F2", size=size))
        self.current_y -= size + after

    def bullet_lines(self, items: list[str]) -> list[str]:
        width = char_capacity(CONTENT_WIDTH, font_size=BODY_FONT_SIZE, cell_padding=0)
        prepared: list[str] = []
        for item in items:
            prepared.extend(wrap_prefixed(item, width, prefix="- ", continuation="  "))
        return prepared

    def numbered_lines(self, steps: list[str]) -> list[str]:
        width = char_capacity(CONTENT_WIDTH, font_size=BODY_FONT_SIZE, cell_padding=0)
        prepared: list[str] = []
        for index, step in enumerate(steps, start=1):
            prefix = f"{index}. "
            prepared.extend(
                wrap_prefixed(step, width, prefix=prefix, continuation=" " * len(prefix))
            )
        return prepared

    def code_lines(self, lines: list[str]) -> list[str]:
        inner_width = CONTENT_WIDTH - 12
        width = char_capacity(inner_width, font_size=CODE_FONT_SIZE, cell_padding=0)
        prepared: list[str] = []
        for line in lines:
            wrapped = textwrap.wrap(
                line,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            ) or [""]
            prepared.extend(wrapped)
        return prepared

    def add_paragraph(
        self, text: str, *, size: int = BODY_FONT_SIZE, before: int = 0, after: int = 6
    ) -> None:
        width = char_capacity(CONTENT_WIDTH, font_size=size, cell_padding=0)
        lines = wrap_prefixed(text, width)
        height = before + (len(lines) * BODY_LINE_HEIGHT) + after
        self.ensure_space(height)
        self.current_y -= before
        for line in lines:
            self.commands.append(text_command(line, MARGIN, self.current_y, size=size))
            self.current_y -= BODY_LINE_HEIGHT
        self.current_y -= after

    def add_bullets(self, items: list[str], *, before: int = 0, after: int = 6) -> None:
        prepared = self.bullet_lines(items)
        height = before + (len(prepared) * BODY_LINE_HEIGHT) + after
        self.ensure_space(height)
        self.current_y -= before
        for line in prepared:
            self.commands.append(text_command(line, MARGIN, self.current_y, size=BODY_FONT_SIZE))
            self.current_y -= BODY_LINE_HEIGHT
        self.current_y -= after

    def add_numbered_steps(self, steps: list[str], *, before: int = 0, after: int = 6) -> None:
        prepared = self.numbered_lines(steps)
        height = before + (len(prepared) * BODY_LINE_HEIGHT) + after
        self.ensure_space(height)
        self.current_y -= before
        for line in prepared:
            self.commands.append(text_command(line, MARGIN, self.current_y, size=BODY_FONT_SIZE))
            self.current_y -= BODY_LINE_HEIGHT
        self.current_y -= after

    def add_code_block(self, lines: list[str], *, before: int = 0, after: int = 8) -> None:
        prepared = self.code_lines(lines)
        block_height = 8 + (len(prepared) * CODE_LINE_HEIGHT) + 6
        total_height = before + block_height + after
        self.ensure_space(total_height)
        self.current_y -= before

        top = self.current_y
        bottom = top - block_height
        self.commands.append(rectangle_command(MARGIN, bottom, CONTENT_WIDTH, block_height))

        text_y = top - 12
        for line in prepared:
            self.commands.append(text_command(line, MARGIN + 6, text_y, size=CODE_FONT_SIZE))
            text_y -= CODE_LINE_HEIGHT

        self.current_y = bottom - after

    def add_role_block(self, guide: RoleProvisioningGuide) -> None:
        self.add_heading(f"{guide.label} ({guide.code})", before=12, after=4)
        self.add_paragraph(guide.purpose, after=4)
        self.add_bullets(
            [
                f"Go-live JSON path: {guide.json_path}",
                f"is_staff: {'true' if guide.is_staff else 'false'}",
                f"is_superuser: {'true' if guide.is_superuser else 'false'}",
                f"UserShopAccess required: {'yes' if guide.shop_access_required else 'no'}",
            ],
            after=6,
        )
        initializer_height = (
            len(self.numbered_lines(guide.initializer_steps)) * BODY_LINE_HEIGHT
        ) + 12
        self.add_heading(
            "Go-live initializer",
            size=11,
            before=0,
            after=3,
            keep_with_next=initializer_height,
        )
        self.add_numbered_steps(guide.initializer_steps, after=6)
        code_height = 8 + (len(self.code_lines(guide.json_example)) * CODE_LINE_HEIGHT) + 14
        self.add_heading(
            "Example JSON",
            size=11,
            before=0,
            after=3,
            keep_with_next=code_height,
        )
        self.add_code_block(guide.json_example, after=6)
        admin_height = (len(self.numbered_lines(guide.admin_steps)) * BODY_LINE_HEIGHT) + 12
        self.add_heading(
            "Django admin",
            size=11,
            before=0,
            after=3,
            keep_with_next=admin_height,
        )
        self.add_numbered_steps(guide.admin_steps, after=4)
        if guide.notes:
            notes_height = (len(self.bullet_lines(guide.notes)) * BODY_LINE_HEIGHT) + 12
            self.add_heading("Notes", size=11, before=0, after=3, keep_with_next=notes_height)
            self.add_bullets(guide.notes, after=6)
        self.ensure_space(12)
        self.commands.append(
            line_command(MARGIN, self.current_y, PAGE_WIDTH - MARGIN, self.current_y)
        )
        self.current_y -= 10


def build_pages(generated_on: str) -> list[str]:
    renderer = ProvisioningGuideRenderer(generated_on)

    renderer.add_heading("Overview", before=0, after=4)
    renderer.add_bullets(GENERAL_RULES, after=8)

    renderer.add_heading("Quick Reference", before=0, after=4)
    renderer.add_bullets(
        [
            f"{guide.label} ({guide.code}): json path {guide.json_path}, "
            f"is_staff={'true' if guide.is_staff else 'false'}, "
            f"is_superuser={'true' if guide.is_superuser else 'false'}, "
            f"UserShopAccess={'required' if guide.shop_access_required else 'not required'}."
            for guide in ROLE_GUIDES
        ],
        after=10,
    )

    for guide in ROLE_GUIDES:
        renderer.add_role_block(guide)

    return renderer.finish()


def write_pdf(output_path: Path, pages: list[str]) -> None:
    builder = PDFBuilder()
    regular_font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    bold_font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>")

    content_ids = [builder.add_object(stream_object(page)) for page in pages]
    pages_id = builder.reserve_object_id()
    page_ids = []

    for content_id in content_ids:
        page_ids.append(
            builder.add_object(
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {regular_font_id} 0 R /F2 {bold_font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
        )

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
    pages = build_pages(args.generated_on)
    write_pdf(Path(args.output), pages)


if __name__ == "__main__":
    main()
