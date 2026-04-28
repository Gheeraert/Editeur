from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Heading, InlineSpan, InlineStyle, Metadata, Note, Paragraph
from purh_editorial.serialization import to_json, to_plain_data


class ModelAndSerializationTests(unittest.TestCase):
    def test_document_dataclass_serialization(self) -> None:
        document = Document(
            document_id="doc-test",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            metadata=Metadata(title="Titre test", authors=["Auteur"]),
            blocks=[
                Heading(block_id="h1", text="Titre"),
                Paragraph(
                    block_id="p1",
                    text="Texte",
                    inlines=[
                        InlineSpan(text="Texte", style=InlineStyle(italic=True)),
                        InlineSpan(text="[1]", kind="note_call", note_ref="ftn1"),
                    ],
                    note_refs=["ftn1"],
                ),
            ],
            notes=[
                Note(
                    note_id="ftn1",
                    label="1",
                    text="Note",
                    inlines=[InlineSpan(text="Note", style=InlineStyle(bold=True))],
                )
            ],
        )

        payload = to_plain_data(document)
        self.assertEqual(payload["document_id"], "doc-test")
        self.assertEqual(payload["metadata"]["title"], "Titre test")
        self.assertEqual(payload["blocks"][0]["block_type"], "heading")
        self.assertEqual(payload["blocks"][1]["inlines"][0]["style"]["italic"], True)
        self.assertEqual(payload["notes"][0]["inlines"][0]["style"]["bold"], True)

        serialized = to_json(document)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["blocks"][1]["text"], "Texte")
        self.assertEqual(parsed["blocks"][1]["inlines"][1]["note_ref"], "ftn1")


if __name__ == "__main__":
    unittest.main()
