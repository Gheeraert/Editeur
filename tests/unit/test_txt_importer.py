from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io import ImporterRegistry


class TxtImporterTests(unittest.TestCase):
    def test_load_txt_fixture(self) -> None:
        fixture = Path("tests/fixtures/minimal_source.txt")
        document = ImporterRegistry().load_document(fixture)

        self.assertEqual(document.source_format, "txt")
        self.assertGreaterEqual(len(document.blocks), 3)
        self.assertEqual(document.blocks[0].block_type, "heading")
        self.assertIn("exemple", document.blocks[1].text.lower())


if __name__ == "__main__":
    unittest.main()
