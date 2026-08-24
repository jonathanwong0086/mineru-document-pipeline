from __future__ import annotations

import re
from typing import Any


def normalize_markdown(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    previous = None
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^(?:页码|page)\s*[:：]?\s*\d+$", stripped, re.I):
            flags.append("page_furniture_removed")
            continue
        if re.match(r"^!\[[^\]]*\]\([^)]*\)$", stripped):
            flags.append("image_placeholder_removed")
            continue
        if stripped and stripped == previous:
            flags.append("duplicate_line_removed")
            continue
        lines.append(line.rstrip())
        if stripped:
            previous = stripped
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return (cleaned + "\n" if cleaned else ""), sorted(set(flags))


def split_table_rows(caption: str, rows: list[str], *, max_rows: int = 50) -> list[dict[str, Any]]:
    if not rows:
        return []
    header = rows[0]
    data = rows[1:]
    width = max(1, int(max_rows))
    chunks: list[dict[str, Any]] = []
    for index in range(0, len(data), width):
        body = data[index:index + width]
        prefix = f"{caption}\n\n" if caption else ""
        chunks.append({
            "text": prefix + "\n".join([header, *body]),
            "continuation": index > 0,
            "row_start": index + 1,
            "row_end": index + len(body),
        })
    return chunks
