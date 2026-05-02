from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io import ImporterRegistry
from tests.helpers.docx_factory import (
    create_blank_separated_docx,
    create_rich_docx,
    create_table_docx,
)


class RichDocxImporterTests(unittest.TestCase):
    @staticmethod
    def _runtime_docx_path() -> Path:
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / f"rich_{uuid.uuid4().hex}.docx"

    def test_import_docx_preserves_inline_styles_and_note_call(self) -> None:
        docx_path = self._runtime_docx_path()
        create_rich_docx(docx_path)
        document = ImporterRegistry().load_document(docx_path)

        self.assertEqual(document.source_format, "docx")
        self.assertEqual(len(document.blocks), 1)
        block = document.blocks[0]
        self.assertTrue(block.inlines)
        self.assertIn("ftn2", block.note_refs)

        italic_span = next((span for span in block.inlines if "italique" in span.text), None)
        bold_span = next((span for span in block.inlines if "gras" in span.text), None)
        small_caps_span = next((span for span in block.inlines if "sc" in span.text), None)
        sub_span = next((span for span in block.inlines if "sub" in span.text), None)
        super_span = next((span for span in block.inlines if "sup" in span.text and span.kind == "text"), None)
        note_call_span = next((span for span in block.inlines if span.kind == "note_call"), None)

        self.assertIsNotNone(italic_span)
        self.assertTrue(italic_span.style.italic)
        self.assertIsNotNone(bold_span)
        self.assertTrue(bold_span.style.bold)
        self.assertIsNotNone(small_caps_span)
        self.assertTrue(small_caps_span.style.small_caps)
        self.assertIsNotNone(sub_span)
        self.assertTrue(sub_span.style.subscript)
        self.assertIsNotNone(super_span)
        self.assertTrue(super_span.style.superscript)
        self.assertIsNotNone(note_call_span)
        self.assertEqual(note_call_span.note_ref, "ftn2")

    def test_import_docx_note_keeps_inline_styles(self) -> None:
        docx_path = self._runtime_docx_path()
        create_rich_docx(docx_path)
        document = ImporterRegistry().load_document(docx_path)

        self.assertEqual(len(document.notes), 1)
        note = document.notes[0]
        self.assertEqual(note.note_id, "ftn2")
        self.assertTrue(note.inlines)
        self.assertEqual(note.target_ref, document.blocks[0].block_id)

        note_italic = next((span for span in note.inlines if "italique" in span.text), None)
        note_bold = next((span for span in note.inlines if "gras" in span.text), None)
        note_small_caps = next((span for span in note.inlines if "sc" in span.text), None)
        note_sub = next((span for span in note.inlines if "sub" in span.text), None)
        note_super = next((span for span in note.inlines if "sup" in span.text), None)

        self.assertIsNotNone(note_italic)
        self.assertTrue(note_italic.style.italic)
        self.assertIsNotNone(note_bold)
        self.assertTrue(note_bold.style.bold)
        self.assertIsNotNone(note_small_caps)
        self.assertTrue(note_small_caps.style.small_caps)
        self.assertIsNotNone(note_sub)
        self.assertTrue(note_sub.style.subscript)
        self.assertIsNotNone(note_super)
        self.assertTrue(note_super.style.superscript)

    def test_import_docx_preserves_table_as_protected_block(self) -> None:
        docx_path = self._runtime_docx_path()
        create_table_docx(docx_path)
        document = ImporterRegistry().load_document(docx_path)

        self.assertEqual(len(document.blocks), 3)
        self.assertEqual(document.blocks[0].block_type, "paragraph")
        self.assertEqual(document.blocks[0].text.strip(), "Avant tableau")
        self.assertEqual(document.blocks[1].block_type, "table")
        self.assertEqual(document.blocks[1].attributes.get("protected_zone"), "table")
        self.assertIn("<", document.blocks[1].attributes.get("table_ooxml", ""))
        self.assertEqual(document.blocks[2].block_type, "paragraph")
        self.assertEqual(document.blocks[2].text.strip(), "Après tableau")
        self.assertTrue(document.annotations.get("table_detected"))
        self.assertTrue(document.annotations.get("table_preserved"))
        self.assertTrue(document.annotations.get("table_protected"))

    def test_import_docx_marks_blank_paragraph_boundaries(self) -> None:
        docx_path = self._runtime_docx_path()
        create_blank_separated_docx(docx_path)
        document = ImporterRegistry().load_document(docx_path)

        # Les deux paragraphes vides du DOCX sont supprimés comme blocs,
        # mais leur trace doit rester exploitable pour le service de structure.
        self.assertEqual(len(document.blocks), 6)
        self.assertEqual(document.blocks[0].text.strip(), "Prose avant le bloc.")
        self.assertTrue(document.blocks[0].attributes.get("blank_para_after"))
        self.assertTrue(document.blocks[1].attributes.get("blank_para_before"))
        self.assertEqual(document.blocks[1].attributes.get("blank_para_before_count"), 1)
        self.assertTrue(document.blocks[4].attributes.get("blank_para_after"))
        self.assertTrue(document.blocks[5].attributes.get("blank_para_before"))
        self.assertEqual(document.blocks[4].attributes.get("blank_para_after_count"), 1)


if __name__ == "__main__":
    unittest.main()
