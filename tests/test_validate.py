import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from publish import publish_bundle  # noqa: E402
from validate import validate_published  # noqa: E402


class ValidateTests(unittest.TestCase):
    def test_valid_bundle_passes_all_lane_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = {"doc_id": "T1", "canonical_name": "T1测试", "title": "测试", "chunks": [{"chunk_id": "T1-1", "text": "正文", "content_type": "text", "page_start": 1, "page_end": 1}]}
            publish_bundle(bundle, "# 测试\n\n正文\n", root)
            report = validate_published(root, "T1测试")
            self.assertTrue(report["ok"])
            self.assertEqual(report["errors"], [])

    def test_missing_json_chunk_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "database_json").mkdir(parents=True)
            (root / "rag_markdown").mkdir()
            (root / "human_doc").mkdir()
            (root / "database_json" / "bad.json").write_text(json.dumps({"chunks": []}), encoding="utf-8")
            (root / "rag_markdown" / "bad.md").write_text("# bad", encoding="utf-8")
            report = validate_published(root, "bad")
            self.assertFalse(report["ok"])
            self.assertTrue(any("chunks" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
