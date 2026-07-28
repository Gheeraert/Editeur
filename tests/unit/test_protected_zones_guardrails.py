from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, Note, Paragraph, QuoteBlock
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.orthotypo_service import NNBSP, OrthotypoService


class ProtectedZonesGuardrailsTests(unittest.TestCase):
    def test_orthotypography_skips_every_protected_zone(self) -> None:
        protected_blocks = [
            QuoteBlock(block_id="quote", text="Citation: intacte"),
            Paragraph(block_id="poetry", text="Vers: intact", attributes={"protected_zone": "poetry"}),
            Paragraph(block_id="code", text="Code: intact", attributes={"protected_zone": "code"}),
            Paragraph(block_id="transcription", text="Transcription: intact", attributes={"protected_zone": "linguistic_transcription"}),
            Paragraph(block_id="biblio", text="DUPONT: 2024", attributes={"protected_zone": "bibliography"}),
            Paragraph(
                block_id="inline",
                text="Occurrence: intacte",
                inlines=[InlineSpan(text="Occurrence: intacte", attributes={"protected_zone": "quote"})],
            ),
        ]
        ordinary = Paragraph(block_id="ordinary", text="Prose n° 5")
        document = Document("doc", "fixture", "txt", blocks=[*protected_blocks, ordinary])

        corrected, transformations = OrthotypoService().apply(document)

        self.assertEqual([block.text for block in corrected.blocks[:-1]], [block.text for block in protected_blocks])
        self.assertEqual(corrected.blocks[-1].text, f"Prose no{NNBSP}5")
        self.assertEqual({tr.target_ref for tr in transformations}, {"ordinary"})

    def test_unvalidated_rule_becomes_a_diagnostic_not_a_correction(self) -> None:
        document = Document("doc", "fixture", "txt", blocks=[Paragraph(block_id="p1", text="Voici: un cas")])

        corrected, transformations = OrthotypoService().apply(document)
        diagnostics = OrthotypoService().analyze_unvalidated_rules(corrected)

        self.assertEqual(corrected.blocks[0].text, "Voici: un cas")
        self.assertEqual(transformations, [])
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].rule_id, "purh.espaces.avant_ponct_forte")

    def test_note_in_protected_block_or_zone_is_not_normalized(self) -> None:
        document = Document(
            "doc", "fixture", "txt",
            blocks=[QuoteBlock(block_id="quote", text="Citation")],
            notes=[
                Note(note_id="n1", target_ref="quote", text="note sans point"),
                Note(note_id="n2", text="autre note sans point", attributes={"protected_zone": "code"}),
                Note(note_id="n3", text="note ordinaire sans point"),
            ],
        )

        corrected, transformations = FootnoteNormalizer().apply(document)

        self.assertEqual(corrected.notes[0].text, "note sans point")
        self.assertEqual(corrected.notes[1].text, "autre note sans point")
        self.assertEqual(corrected.notes[2].text, "Note ordinaire sans point.")
        self.assertEqual({tr.target_ref for tr in transformations}, {"n3"})
