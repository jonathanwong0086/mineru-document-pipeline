import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from preflight import canonical_name, inspect_file  # noqa: E402
from split import split_pdf  # noqa: E402


class PreflightSplitTests(unittest.TestCase):
    def test_canonical_name_removes_spacing_and_year_suffix(self):
        code, title, name = canonical_name("GB 50016-2014 建筑设计防火规范(2018年版)-新华院.pdf")
        self.assertEqual(code, "GB50016")
        self.assertEqual(title, "建筑设计防火规范")
        self.assertEqual(name, "GB50016建筑设计防火规范")

    def test_inspect_file_reports_pages_size_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with path.open("wb") as handle:
                writer.write(handle)
            record = inspect_file(path)
            self.assertEqual(record["page_count"], 1)
            self.assertGreater(record["size_bytes"], 0)
            self.assertEqual(len(record["sha256"]), 64)

    def test_split_pdf_preserves_order_and_page_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "book.pdf"
            writer = PdfWriter()
            for _ in range(5):
                writer.add_blank_page(width=100, height=100)
            with source.open("wb") as handle:
                writer.write(handle)
            parts, manifest = split_pdf(source, Path(tmp) / "parts", max_pages=2, max_size_mb=200)
            self.assertEqual(len(parts), 3)
            self.assertEqual([item["page_start"] for item in manifest], [1, 3, 5])
            self.assertEqual([len(PdfReader(str(path)).pages) for path in parts], [2, 2, 1])


if __name__ == "__main__":
    unittest.main()
