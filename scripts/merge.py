from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from normalize import normalize_markdown


def _structured_file(part_dir: Path) -> Path | None:
    extracted = part_dir / "extracted"
    candidates = list(extracted.glob("*_content_list_v2.json")) + list(extracted.glob("content_list_v2.json"))
    return candidates[0] if candidates else None


def _payload(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        flattened: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                flattened.append(item)
            elif isinstance(item, list):
                flattened.extend(block for block in item if isinstance(block, dict))
        return flattened
    for key in ("content_list", "items", "data", "blocks"):
        if isinstance(value.get(key), list):
            return [item for item in value[key] if isinstance(item, dict)]
    return []


def _block_text(block: dict[str, Any]) -> str:
    for key in ("text", "content", "md", "value"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    content = block.get("content")
    if isinstance(content, dict):
        for key in ("paragraph_content", "title_content", "text_content", "list_content", "table_caption", "table_footnote"):
            items = content.get(key)
            if isinstance(items, list):
                values = []
                for item in items:
                    if isinstance(item, dict) and isinstance(item.get("content"), str):
                        values.append(item["content"].strip())
                    elif isinstance(item, str):
                        values.append(item.strip())
                if values:
                    return "\n".join(value for value in values if value)
    return ""


def merge_part_results(part_dirs: list[str | Path], *, source_page_offsets: list[int] | None = None) -> dict[str, Any]:
    offsets = source_page_offsets or [0] * len(part_dirs)
    markdowns: list[str] = []
    chunks: list[dict[str, Any]] = []
    for part_index, raw_dir in enumerate(part_dirs):
        part_dir = Path(raw_dir)
        md = part_dir / "extracted" / "full.md"
        if not md.exists():
            md = part_dir / "full.md"
        if md.exists():
            markdowns.append(normalize_markdown(md.read_text(encoding="utf-8", errors="replace"))[0])
        structured = _structured_file(part_dir)
        if not structured:
            continue
        for block_index, block in enumerate(_payload(structured), 1):
            text = _block_text(block)
            if not text:
                continue
            raw_page = block.get("page_idx", block.get("page_no", 0))
            try:
                page = int(raw_page)
            except (TypeError, ValueError):
                page = 0
            if "page_idx" in block:
                page += 1
            page += offsets[part_index]
            content_type = str(block.get("type", block.get("block_type", "text"))).lower()
            if content_type in {"text", "paragraph", "title", "list"}:
                content_type = "text"
            elif content_type in {"table", "image", "figure", "chart", "formula", "code"}:
                content_type = "figure" if content_type == "chart" else content_type
            else:
                content_type = "text"
            chunks.append({
                "chunk_id": f"part{part_index + 1:02d}-p{page}-{content_type}-{block_index:05d}",
                "content_type": content_type,
                "text": text,
                "section": str(block.get("section_title", block.get("section", ""))),
                "page_start": page,
                "page_end": page,
                "part": part_index + 1,
                "cleanup_flags": [],
            })
    return {"markdown": "\n\n".join(x for x in markdowns if x), "chunks": chunks}
