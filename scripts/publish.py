from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from docx import Document


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def _write_docx(path: Path, markdown: str) -> None:
    document = Document()
    for line in markdown.splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith("### "):
            document.add_heading(value[4:], level=3)
        elif value.startswith("## "):
            document.add_heading(value[3:], level=2)
        elif value.startswith("# "):
            document.add_heading(value[2:], level=1)
        else:
            document.add_paragraph(re.sub(r"[`*_]+", "", value))
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)


def _write_doc(path: Path, docx_path: Path) -> bool:
    if os.name != "nt":
        return False
    target = str(path).replace("'", "''")
    source = str(docx_path).replace("'", "''")
    script = (
        "$word=New-Object -ComObject Word.Application; $word.Visible=$false; $word.DisplayAlerts=0; "
        f"$doc=$word.Documents.Open('{source}',$false,$true); $doc.SaveAs2('{target}',0); "
        "$doc.Close($false); $word.Quit()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True, text=True, timeout=120)
        return path.exists() and path.stat().st_size > 0
    except (OSError, subprocess.SubprocessError):
        return False


def publish_bundle(bundle: dict[str, Any], markdown: str, output_root: str | Path) -> dict[str, Path]:
    output_root = Path(output_root)
    name = str(bundle["canonical_name"])
    md_path = output_root / "rag_markdown" / f"{name}.md"
    json_path = output_root / "database_json" / f"{name}.json"
    docx_path = output_root / "human_doc" / f"{name}.docx"
    doc_path = output_root / "human_doc" / f"{name}.doc"
    _atomic_text(md_path, markdown)
    _write_docx(docx_path, markdown)
    if _write_doc(doc_path, docx_path):
        bundle.setdefault("warnings", []).append("doc_generated_with_word_com")
    else:
        bundle.setdefault("warnings", []).append("doc_not_generated_word_com_unavailable")
    _atomic_text(json_path, json.dumps(bundle, ensure_ascii=False, indent=2))
    return {"markdown": md_path, "json": json_path, "docx": docx_path, "doc": doc_path}
