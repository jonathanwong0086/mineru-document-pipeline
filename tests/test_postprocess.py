import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from merge import merge_part_results  # noqa: E402
from normalize import normalize_markdown, split_table_rows  # noqa: E402
from publish import publish_bundle  # noqa: E402


class PostProcessTests(unittest.TestCase):
    def test_normalize_markdown_removes_page_furniture_but_keeps_body(self):
        raw = "# Title\n\n页码 1\n\n正文内容\n\n正文内容\n\n![](images/a.jpg)\n"
        cleaned, flags = normalize_markdown(raw)
        self.assertIn("正文内容", cleaned)
        self.assertNotIn("页码 1", cleaned)
        self.assertEqual(cleaned.count("正文内容"), 1)
        self.assertIn("image_placeholder_removed", flags)

    def test_split_table_rows_repeats_header_and_marks_continuation(self):
        chunks = split_table_rows("设备参数", ["名称 | 数值", "A | 1", "B | 2", "C | 3"], max_rows=2)
        self.assertEqual(len(chunks), 2)
        self.assertIn("名称 | 数值", chunks[1]["text"])
        self.assertTrue(chunks[1]["continuation"])

    def test_merge_uses_part_page_offsets_and_structured_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part1 = root / "part01" / "extracted"
            part2 = root / "part02" / "extracted"
            part1.mkdir(parents=True)
            part2.mkdir(parents=True)
            (part1 / "full.md").write_text("# One\n\nalpha", encoding="utf-8")
            (part2 / "full.md").write_text("# Two\n\nbeta", encoding="utf-8")
            (part1 / "content_list_v2.json").write_text(json.dumps([{"type": "text", "text": "alpha", "page_idx": 0}], ensure_ascii=False), encoding="utf-8")
            (part2 / "content_list_v2.json").write_text(json.dumps([{"type": "text", "text": "beta", "page_idx": 0}], ensure_ascii=False), encoding="utf-8")
            result = merge_part_results([part1.parent, part2.parent], source_page_offsets=[0, 180])
            self.assertEqual(result["chunks"][1]["page_start"], 181)
            self.assertEqual(len(result["chunks"]), 2)

    def test_merge_flattens_mineru_page_nested_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            part = Path(tmp) / "part" / "extracted"
            part.mkdir(parents=True)
            (part / "full.md").write_text("# Nested\n\n正文", encoding="utf-8")
            payload = [[{"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": "正文"}]}, "page_idx": 0}]]
            (part / "content_list_v2.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = merge_part_results([part.parent])
            self.assertEqual(result["chunks"][0]["text"], "正文")

    def test_publish_bundle_writes_three_lanes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            bundle = {"doc_id": "T1", "canonical_name": "T1测试", "title": "测试", "chunks": [{"chunk_id": "T1-1", "text": "正文", "content_type": "text"}]}
            paths = publish_bundle(bundle, "# 测试\n\n正文\n", out)
            self.assertTrue(paths["markdown"].exists())
            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["docx"].exists())


if __name__ == "__main__":
    unittest.main()
