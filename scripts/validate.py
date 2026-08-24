from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_published(output_root: str | Path, canonical_name: str) -> dict[str, Any]:
    root = Path(output_root)
    errors: list[str] = []
    json_path = root / "database_json" / f"{canonical_name}.json"
    md_path = root / "rag_markdown" / f"{canonical_name}.md"
    docx_path = root / "human_doc" / f"{canonical_name}.docx"
    for path in (json_path, md_path, docx_path):
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing or empty output: {path}")
    data: dict[str, Any] = {}
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid JSON: {exc}")
    chunks = data.get("chunks", []) if isinstance(data, dict) else []
    if not chunks:
        errors.append("database JSON chunks are empty")
    seen: set[str] = set()
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            errors.append(f"chunk {index} is not an object")
            continue
        chunk_id = chunk.get("chunk_id")
        if not chunk_id or chunk_id in seen:
            errors.append(f"chunk {index} has missing or duplicate chunk_id")
        seen.add(str(chunk_id))
        if not str(chunk.get("text", "")).strip():
            errors.append(f"chunk {index} has empty text")
    return {"ok": not errors, "errors": errors, "canonical_name": canonical_name, "chunk_count": len(chunks)}


def validate_manifest(output_root: str | Path, expected_count: int | None = None) -> dict[str, Any]:
    root = Path(output_root)
    manifest_path = root / "manifest.json"
    errors: list[str] = []
    if not manifest_path.exists():
        return {"ok": False, "errors": [f"missing manifest: {manifest_path}"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = manifest.get("documents", [])
    if expected_count is not None and len(documents) != expected_count:
        errors.append(f"manifest count {len(documents)} != expected {expected_count}")
    reports = [validate_published(root, item["name"]) for item in documents if item.get("name")]
    for report in reports:
        errors.extend(report["errors"])
    return {"ok": not errors, "errors": errors, "count": len(documents), "reports": reports}
