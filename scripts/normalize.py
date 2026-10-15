from __future__ import annotations

import re
from typing import Any


# 句末标点后紧跟 "4.1.4 汉字" 这种多级条款号时，视为 OCR 把两条条款并进了同一段。
# 只认 x.y 及以上层级，并要求条款号后是空格加汉字（"条/款/节/章/表/图"除外），
# 避免误拆 "；4.1.3 条另有规定""GB 50160 5.7.2" 之类的引用。
_MERGED_CLAUSE = re.compile(r"(?<=[。；;！!？?])\s*(?=\d{1,2}(?:\.\d{1,3}){1,3}\s+(?![条款节章表图])[一-鿿])")


def split_merged_clauses(line: str) -> tuple[list[str], bool]:
    if "<td" in line or "<table" in line or line.lstrip().startswith(("|", "#")):
        return [line], False
    parts = [part.strip() for part in _MERGED_CLAUSE.split(line)]
    parts = [part for part in parts if part]
    return (parts, True) if len(parts) > 1 else ([line], False)


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
        pieces, was_split = split_merged_clauses(line.rstrip())
        if was_split:
            flags.append("merged_clause_split")
            # 拆出的条款各自成段
            pieces = [item for piece in pieces for item in (piece, "")][:-1]
        lines.extend(pieces)
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
