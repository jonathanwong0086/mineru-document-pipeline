from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def canonical_name(filename: str) -> tuple[str, str, str]:
    stem = Path(filename).stem
    stem = re.sub(r"\s*-\s*新华院\s*$", "", stem)
    match = re.match(r"\s*([A-Za-z]+)\s*([0-9]+(?:\.[0-9]+)?(?:[A-Za-z])?)(?:-[0-9]+)?[\s_]*(.*)$", stem)
    if not match:
        compact = re.sub(r"\s+", "", stem)
        return compact, compact, compact
    prefix, number, title = match.groups()
    code = f"{prefix.upper()}{number}"
    title = re.sub(r"^[\s:：-]+", "", title)
    title = re.sub(r"[《》]", "", title)
    title = re.sub(r"[（(](?:19|20)\d{2}年?版[）)]", "", title)
    title = re.sub(r"[-_\s]+$", "", title)
    # 文件名只有标准号时标题留空，由调用方从正文补全，避免拼成 "GB15603GB15603"
    return code, title, f"{code}{title}"


_COVER_HEADING = re.compile(r"^(?:中华人民共和国.*标准|.*行业标准|.*团体标准|.*地方标准|ICS.*|前言|目次|目录)$")
_CJK = re.compile(r"[一-鿿]")


def title_from_markdown(markdown: str) -> str:
    """从封面区的一级标题里取标准名称，跳过"中华人民共和国国家标准"等版头。"""
    for line in markdown.splitlines()[:80]:
        match = re.match(r"^#\s+(.+)$", line.strip())
        if not match:
            continue
        # OCR 常把封面大字识别成 "危 险 化 学 品"，先去掉汉字之间的空格
        text = re.sub(r"(?<=[一-鿿])\s+(?=[一-鿿])", "", match.group(1)).strip()
        if not _CJK.search(text) or _COVER_HEADING.match(text):
            continue
        return re.sub(r"[\/:*?\"<>|]", "", text)
    return ""


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
