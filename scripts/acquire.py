from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from http.client import HTTPSConnection
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ErrorInfo:
    code: str
    retryable: bool
    quota: bool = False


def classify_error(code: str | int | None, message: str = "") -> ErrorInfo:
    text = (message or "").lower()
    value = str(code) if code is not None else ""
    if value in {"-10001", "-60001", "-60007", "-60008", "-60009", "-60010", "-60020", "-60021", "-60022"} or "429" in text or "too many requests" in text:
        return ErrorInfo(value, True)
    if "temporary" in text or "try again later" in text or "service unavailable" in text:
        return ErrorInfo(value or "UNKNOWN", True)
    if value in {"-60018", "-60019"}:
        return ErrorInfo(value, False, quota=True)
    return ErrorInfo(value or "UNKNOWN", False)


def retry_call(operation: Callable[[], Any], *, max_retries: int = 3, sleep: Callable[[float], None] = time.sleep) -> Any:
    attempt = 0
    while True:
        try:
            return operation()
        except Exception as exc:
            if attempt >= max_retries or not classify_error(None, str(exc)).retryable:
                raise
            attempt += 1
            sleep(min(60.0, (2**attempt) + random.random()))


class CheckpointStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)


def build_standard_body(
    file_name: str,
    *,
    model_version: str = "vlm",
    language: str = "ch",
    ocr: bool = False,
    enable_table: bool = True,
    enable_formula: bool = True,
    extra_formats: list[str] | None = None,
    page_ranges: str | None = None,
) -> dict[str, Any]:
    file_data: dict[str, Any] = {
        "name": file_name,
        "is_ocr": ocr,
        "enable_table": enable_table,
        "enable_formula": enable_formula,
        "language": language,
    }
    if page_ranges:
        file_data["page_ranges"] = page_ranges
    return {
        "files": [file_data],
        "model_version": model_version,
        "extra_formats": extra_formats or ["docx"],
    }


def _json_request(method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc


def _put_file(url: str, path: Path) -> int:
    parsed = urllib.parse.urlsplit(url)
    connection = HTTPSConnection(parsed.netloc, timeout=300)
    target = urllib.parse.urlunsplit(("", "", parsed.path, parsed.query, ""))
    connection.putrequest("PUT", target)
    connection.putheader("Content-Length", str(path.stat().st_size))
    connection.endheaders()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            connection.send(block)
    response = connection.getresponse()
    response.read()
    connection.close()
    return response.status


def _safe_extract(zip_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    root = output_dir.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (output_dir / member.filename).resolve()
            if not str(target).startswith(str(root)):
                raise RuntimeError(f"unsafe zip member: {member.filename}")
            archive.extract(member, output_dir)


class MineruStandardClient:
    def __init__(self, token: str | None = None, base_url: str = "https://mineru.net"):
        self.token = (token or os.environ.get("MINERU_API_KEY", "")).strip()
        if not self.token:
            raise RuntimeError("MINERU_API_KEY is required for Standard API")
        self.base_url = base_url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json", "Accept": "*/*"}

    def process_part(self, part: str | Path, output_dir: str | Path, *, body: dict[str, Any] | None = None, timeout: int = 1800, poll_seconds: int = 5) -> Path:
        part = Path(part).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = CheckpointStore(output_dir / "checkpoint.json")
        existing = checkpoint.load()
        if existing and existing.get("state") == "done" and (output_dir / "result.zip").exists():
            return output_dir
        request_body = body or build_standard_body(part.name)
        created = _json_request("POST", f"{self.base_url}/api/v4/file-urls/batch", self.headers, request_body)
        if created.get("code") != 0:
            raise RuntimeError(f"{created.get('code')}: {created.get('msg')}")
        batch_id = created["data"]["batch_id"]
        upload_url = created["data"]["file_urls"][0]
        status = _put_file(upload_url, part)
        if status not in {200, 201}:
            raise RuntimeError(f"upload HTTP {status}")
        checkpoint.save({"state": "uploaded", "batch_id": batch_id, "source": part.name})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = _json_request("GET", f"{self.base_url}/api/v4/extract-results/batch/{batch_id}", self.headers)
            if result.get("code") != 0:
                raise RuntimeError(f"{result.get('code')}: {result.get('msg')}")
            entry = (result.get("data", {}).get("extract_result") or [{}])[0]
            state = entry.get("state")
            if state == "done":
                zip_path = output_dir / "result.zip"
                with urllib.request.urlopen(entry["full_zip_url"], timeout=300) as response:
                    zip_path.write_bytes(response.read())
                _safe_extract(zip_path, output_dir / "extracted")
                checkpoint.save({"state": "done", "batch_id": batch_id, "source": part.name})
                return output_dir
            if state == "failed":
                raise RuntimeError(f"{entry.get('err_code')}: {entry.get('err_msg')}")
            time.sleep(poll_seconds)
        raise TimeoutError(f"MinerU timeout: {part.name}")


def process_parts(parts: list[Path], output_root: str | Path, *, workers: int = 6, client_factory: Callable[[], MineruStandardClient] | None = None) -> list[Path]:
    output_root = Path(output_root)
    factory = client_factory or MineruStandardClient

    def work(part: Path) -> Path:
        client = factory()
        return retry_call(lambda: client.process_part(part, output_root / part.stem), max_retries=3)

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
        futures = [executor.submit(work, part) for part in parts]
        return [future.result() for future in as_completed(futures)]
