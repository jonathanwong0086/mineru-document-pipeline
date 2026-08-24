import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pipeline import _source_files  # noqa: E402


class PipelineTests(unittest.TestCase):
    def test_source_files_recurses_supported_extensions(self):
        self.assertEqual(_source_files(Path("missing-input")), [])


if __name__ == "__main__":
    unittest.main()
