import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from preflight import canonical_name, inspect_file, title_from_markdown  # noqa: E402
from split import split_pdf  # noqa: E402


class PreflightSplitTests(unittest.TestCase):
    def test_canonical_name_removes_spacing_and_year_suffix(self):
        code, title, name = canonical_name("GB 50016-2014 建筑设计防火规范(2018年版)-新华院.pdf")
        self.assertEqual(code, "GB50016")
        self.assertEqual(title, "建筑设计防火规范")
        self.assertEqual(name, "GB50016建筑设计防火规范")

    def test_canonical_name_keeps_dotted_part_number(self):
        code, title, name = canonical_name("HGT 20570.2-95《安全阀的设置和选用》.PDF")
        self.assertEqual((code, title, name), ("HGT20570.2", "安全阀的设置和选用", "HGT20570.2安全阀的设置和选用"))

    def test_canonical_name_handles_title_before_code_and_suffixes(self):
        cases = {
            "工业金属管道设计规范GB50316-2000 (2008年版).pdf": "GB50316工业金属管道设计规范",
            "过程测量与控制仪表的功能标志及图形符号-HGT 20505-2000.pdf": "HGT20505过程测量与控制仪表的功能标志及图形符号",
            "SHT 3101-2017 石油化工流程图图例_可搜索.pdf": "SHT3101石油化工流程图图例",
            "HGT 20570.8-95; 气-液分离器设计.pdf": "HGT20570.8气-液分离器设计",
        }
        for filename, expected in cases.items():
            self.assertEqual(canonical_name(filename)[2], expected, filename)

    def test_canonical_name_with_code_only_leaves_title_empty(self):
        code, title, name = canonical_name("GB15603-2022.pdf")
        self.assertEqual((code, title, name), ("GB15603", "", "GB15603"))

    def test_title_from_markdown_skips_cover_banner(self):
        md = "# 中 华 人 民 共 和 国 国 家 标 准\n\nGB 15603—2022\n\n# 危险化学品储存通则\n\n# General rules\n"
        self.assertEqual(title_from_markdown(md), "危险化学品储存通则")

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
