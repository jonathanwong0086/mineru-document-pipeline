import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from acquire import (  # noqa: E402
    CheckpointStore,
    build_standard_body,
    classify_error,
    retry_call,
)


class AcquireTests(unittest.TestCase):
    def test_standard_body_contains_file_options_and_docx(self):
        body = build_standard_body("scan.pdf", language="ch", ocr=True)
        self.assertEqual(body["model_version"], "vlm")
        self.assertEqual(body["extra_formats"], ["docx"])
        self.assertTrue(body["files"][0]["is_ocr"])
        self.assertTrue(body["files"][0]["enable_table"])

    def test_transient_error_is_retryable_but_page_limit_is_not(self):
        self.assertTrue(classify_error(-60010).retryable)
        self.assertTrue(classify_error(-60009).retryable)
        self.assertTrue(classify_error(None, "HTTP 429 too many requests").retryable)
        self.assertFalse(classify_error(-60006).retryable)

    def test_retry_call_retries_transient_failure(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("-60010 temporary parse failure")
            return "done"

        result = retry_call(operation, max_retries=3, sleep=lambda _: None)
        self.assertEqual(result, "done")
        self.assertEqual(len(calls), 3)

    def test_checkpoint_store_writes_and_reads_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CheckpointStore(Path(tmp) / "part.json")
            store.save({"state": "done", "part": 1})
            self.assertEqual(store.load()["state"], "done")


if __name__ == "__main__":
    unittest.main()
