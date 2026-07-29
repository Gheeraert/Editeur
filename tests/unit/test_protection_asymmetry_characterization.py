from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, Note, Paragraph
from purh_editorial.services.bibliography_normalizer import BibliographyNormalizer
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.structure_service import StructurePreparationService


PROTECTED_BLOCK_TYPES = (
    "quote_block",
    "lineated_block",
    "bibliography_item",
    "code",
    "table",
    "formula",
)


def _document(block: Paragraph, *, notes: list[Note] | None = None) -> Document:
    return Document("doc-protection-asymmetry", "fixture.txt", "txt", blocks=[block], notes=notes or [])


class ProtectionAsymmetryCharacterizationTests(unittest.TestCase):
    def test_orthotypography_is_silent_in_every_builtin_protected_block_type_and_protected_inline(self) -> None:
        service = OrthotypoService()
        for block_type in PROTECTED_BLOCK_TYPES:
            with self.subTest(block_type=block_type):
                source = "Voici: n° 5"
                block = Paragraph("p1", text=source, block_type=block_type)
                corrected, transformations = service.apply(_document(block))
                diagnostics = service.analyze_unvalidated_rules(corrected)
                self.assertEqual(corrected.blocks[0].text, source)
                self.assertEqual(transformations, [])
                self.assertEqual(diagnostics, [])

        source = "Voici: n° 5"
        block = Paragraph("inline", text=source, inlines=[InlineSpan(text=source, attributes={"protected": True})])
        corrected, transformations = service.apply(_document(block))
        self.assertEqual(corrected.blocks[0].text, source)
        self.assertEqual(transformations, [])

    def test_notes_inherit_builtin_block_protection_but_ordinary_note_changes(self) -> None:
        service = FootnoteNormalizer()
        for block_type in PROTECTED_BLOCK_TYPES:
            with self.subTest(block_type=block_type):
                source = "note sans point"
                document = _document(
                    Paragraph("p1", text="Bloc", block_type=block_type),
                    notes=[Note("n1", text=source, target_ref="p1")],
                )
                corrected, transformations = service.apply(document)
                self.assertEqual(corrected.notes[0].text, source)
                self.assertEqual(transformations, [])

        ordinary = _document(
            Paragraph("ordinary", text="Bloc"),
            notes=[Note("n1", text="note sans point", target_ref="ordinary")],
        )
        corrected, transformations = service.apply(ordinary)
        self.assertEqual(corrected.notes[0].text, "Note sans point.")
        self.assertTrue(transformations)

    def test_bibliography_owner_processes_its_own_builtin_type_unless_protection_is_explicit(self) -> None:
        service = BibliographyNormalizer()
        entry = Paragraph("b1", text="Dupont, Jean, Essai, p. 12", block_type="bibliography_item")
        corrected, transformations = service.apply(_document(entry))
        self.assertEqual(corrected.blocks[0].text, "Dupont, Jean, Essai, p.\u202f12.")
        self.assertEqual(
            {item.rule_id for item in transformations},
            {"purh.biblio.pagination_nnbsp", "purh.biblio.ponctuation_finale"},
        )

        vetoed = Paragraph(
            "b2",
            text="Dupont, Jean, Essai, p. 12",
            block_type="bibliography_item",
            attributes={"protected_zone": "bibliography"},
        )
        corrected, transformations = service.apply(_document(vetoed))
        self.assertEqual(corrected.blocks[0].text, "Dupont, Jean, Essai, p. 12")
        self.assertEqual(transformations, [])

    def test_structure_has_no_matching_explicit_protection_veto_for_a_paragraph(self) -> None:
        service = StructurePreparationService()
        ordinary = Paragraph("ordinary", text="TITRE PRINCIPAL", attributes={"all_runs_bold": True})
        protected = Paragraph(
            "protected",
            text="TITRE PRINCIPAL",
            attributes={"all_runs_bold": True, "protected_zone": "code"},
        )
        ordinary_document = _document(ordinary)
        protected_document = _document(protected)

        service.process(ordinary_document, mode="heuristic")
        diagnostics, transformations = service.process(protected_document, mode="heuristic")

        self.assertEqual(ordinary_document.blocks[0].block_type, "heading")
        self.assertEqual(protected_document.blocks[0].block_type, "heading")
        self.assertIn("structure.allcaps.heading", {item.rule_id for item in transformations})
        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
