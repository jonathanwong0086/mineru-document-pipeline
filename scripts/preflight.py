from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def canonical_name(filename: str) -> tuple[str, str, str]:
    stem = Path(filename).stem
    stem = re.sub(r"\s*-\s*新华院\s*$", "", stem)
    match = re.match(r"\s*([A-Za-z]+)\s*([0-9]+(?:[A-Za-z])?)(?:-[0-9]+)?[\s_]*(.*)$", stem)
    if not match:
        compact = re.sub(r"\s+", "", stem)
        return compact, compact, compact
    prefix, number, title = match.groups()
    code = f"{prefix.upper()}{number}"
    title = re.sub(r"^[\s:：-]+", "", title)
    title = re.sub(r"[（(](?:19|20)\d{2}年?版[）)]", "", title)
    title = re.sub(r"[-_\s]+$", "", title) or code
    return code, title, f"{code}{title}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _page_count(path: Path) -> int | None:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return len(PdfReader(str(path), strict=False).pages)
    return None


def inspect_file(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    code, title, name = canonical_name(source.name)
    return {
        "source_file": source.name,
        "source_path": str(source),
        "extension": source.suffix.lower(),
        "size_bytes": source.stat().st_size,
        "page_count": _page_count(source),
        "sha256": sha256(source),
        "code": code,
        "title": title,
        "canonical_name": name,
    }
