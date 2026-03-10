from __future__ import annotations

import math

DEFAULT_FONT_SIZE = 10
DEFAULT_CELL_PADDING = 4


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PDFBuilder:
    def __init__(self) -> None:
        self.objects: dict[int, bytes] = {}
        self.next_object_id = 1

    def reserve_object_id(self) -> int:
        object_id = self.next_object_id
        self.next_object_id += 1
        return object_id

    def add_object(self, payload: str | bytes, *, object_id: int | None = None) -> int:
        if object_id is None:
            object_id = self.reserve_object_id()
        data = payload.encode("latin-1") if isinstance(payload, str) else payload
        self.objects[object_id] = data
        return object_id

    def build(self, root_object_id: int) -> bytes:
        parts = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
        offsets = {0: 0}

        for object_id in range(1, self.next_object_id):
            offsets[object_id] = sum(len(part) for part in parts)
            parts.append(f"{object_id} 0 obj\n".encode("ascii"))
            parts.append(self.objects[object_id])
            parts.append(b"\nendobj\n")

        xref_offset = sum(len(part) for part in parts)
        parts.append(f"xref\n0 {self.next_object_id}\n".encode("ascii"))
        parts.append(b"0000000000 65535 f \n")
        for object_id in range(1, self.next_object_id):
            parts.append(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))

        trailer = (
            f"trailer\n<< /Size {self.next_object_id} /Root {root_object_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        )
        parts.append(trailer.encode("ascii"))
        return b"".join(parts)


def stream_object(content: str) -> bytes:
    encoded = content.encode("latin-1")
    return b"<< /Length %d >>\nstream\n%s\nendstream" % (len(encoded), encoded)


def char_capacity(
    width: float,
    *,
    font_size: int = DEFAULT_FONT_SIZE,
    cell_padding: int = DEFAULT_CELL_PADDING,
) -> int:
    usable_width = max(width - (cell_padding * 2), font_size)
    return max(1, math.floor(usable_width / (font_size * 0.6)))


def text_command(
    text: str,
    x: float,
    y: float,
    *,
    font: str = "F1",
    size: int = DEFAULT_FONT_SIZE,
) -> str:
    return f"BT /{font} {size} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({pdf_escape(text)}) Tj ET"


def line_command(x1: float, y1: float, x2: float, y2: float) -> str:
    return f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"


def rectangle_command(x: float, y: float, width: float, height: float) -> str:
    return f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S"
