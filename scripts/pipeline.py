from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from acquire import MineruStandardClient, build_standard_body, process_parts
from merge import merge_part_results
from preflight import canonical_name, inspect_file, title_from_markdown
from publish import publish_bundle
from split import split_pdf
from validate import validate_published


def _source_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    extensions = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".html"}
    return sorted(p for p in input_path.rglob("*") if p.is_file() and p.suffix.lower() in extensions)


def process_one(source: Path, args: argparse.Namespace) -> dict:
    info = inspect_file(source)
    if source.suffix.lower() == ".pdf":
        split_root = args.work_dir / "parts" / info["sha256"]
        parts, part_manifest = split_pdf(source, split_root, max_pages=args.part_pages, max_size_mb=args.part_size_mb)
        output_root = args.work_dir / "mineru"
        body = build_standard_body(source.name, language=args.language, ocr=args.ocr)
        if not args.convert_only:
            process_parts(parts, output_root, workers=args.workers, client_factory=lambda: MineruStandardClient())
        part_dirs = [output_root / part.stem for part in parts]
        if not all((part_dir / "checkpoint.json").exists() for part_dir in part_dirs):
            raise RuntimeError(f"incomplete MinerU parts for {source.name}")
        offsets = [item["page_start"] - 1 for item in part_manifest]
        merged = merge_part_results(part_dirs, source_page_offsets=offsets)
    else:
        output_root = args.work_dir / "mineru"
        part_dir = output_root / source.stem
        part_dir.mkdir(parents=True, exist_ok=True)
        if not args.convert_only:
            client = MineruStandardClient()
            client.process_part(source, part_dir, body=build_standard_body(source.name, language=args.language, ocr=args.ocr))
        merged = merge_part_results([part_dir], source_page_offsets=[0])
    code, title, base_name = canonical_name(source.name)
    if not title:
        title = title_from_markdown(merged["markdown"]) or code
        # base_name 此时是 "GB15603-2022" 这类不带标题的名字，直接把标题接在后面
        if title != code:
            base_name = f"{base_name}{title}"
    merged["doc_id"] = code
    merged["canonical_name"] = base_name
    merged["title"] = title
    merged["source_file"] = source.name
    merged["source_sha256"] = info["sha256"]
    merged["page_count"] = info["page_count"]
    merged["parser"] = {"provider": "mineru", "model": "vlm", "part_pages": args.part_pages, "part_size_mb": args.part_size_mb}
    paths = publish_bundle(merged, f"# {base_name}\n\n{merged['markdown']}", args.output)
    report = validate_published(args.output, base_name)
    if not report["ok"]:
        raise RuntimeError(json.dumps(report, ensure_ascii=False))
    return {"source_file": source.name, "canonical_name": base_name, "paths": {key: str(value) for key, value in paths.items()}, "chunks": report["chunk_count"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="MinerU document pipeline")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("./mineru-output"))
    parser.add_argument("--work-dir", type=Path, default=Path("./.mineru-work"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--part-pages", type=int, default=180)
    parser.add_argument("--part-size-mb", type=int, default=180)
    parser.add_argument("--language", default="ch")
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--convert-only", action="store_true")
    args = parser.parse_args()
    sources = _source_files(args.input)
    if not sources:
        parser.error("no supported files found")
    results = []
    errors = []
    for source in sources:
        try:
            results.append(process_one(source, args))
            print(f"DONE {source.name}")
        except Exception as exc:
            errors.append({"source_file": source.name, "error": str(exc)})
            print(f"FAIL {source.name}: {exc}", file=sys.stderr)
    manifest = {"count": len(results), "requested": len(sources), "documents": results, "errors": errors}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
