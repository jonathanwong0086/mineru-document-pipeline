from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter


def _write_part(reader: PdfReader, start: int, end: int, target: Path) -> None:
    writer = PdfWriter()
    for page in reader.pages[start:end]:
        writer.add_page(page)
    with target.open("wb") as handle:
        writer.write(handle)


def split_pdf(
    source: str | Path,
    output_dir: str | Path,
    *,
    max_pages: int = 180,
    max_size_mb: int = 180,
) -> tuple[list[Path], list[dict[str, Any]]]:
    source = Path(source).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(source), strict=False)
    page_limit = max(1, int(max_pages))
    size_limit = max(1, int(max_size_mb)) * 1024 * 1024
    parts: list[Path] = []
    manifest: list[dict[str, Any]] = []
    start = 0
    part_number = 1
    while start < len(reader.pages):
        end = min(start + page_limit, len(reader.pages))
        while True:
            target = output_dir / f"{source.stem}__part{part_number:02d}.pdf"
            _write_part(reader, start, end, target)
            if target.stat().st_size <= size_limit or end - start <= 1:
                break
            target.unlink()
            end = start + max(1, (end - start) // 2)
        parts.append(target)
        manifest.append({
            "part": part_number,
            "path": str(target),
            "page_start": start + 1,
            "page_end": end,
            "page_count": end - start,
            "size_bytes": target.stat().st_size,
        })
        start = end
        part_number += 1
    (output_dir / "parts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return parts, manifest
