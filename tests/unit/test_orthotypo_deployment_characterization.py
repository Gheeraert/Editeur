from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.orthotypo_service import OrthotypoService, TYPO_RULES


FIXTURES_DIR = ROOT / "fixtures" / "orthotypography_characterization"

EXPECTED_RULE_IDS = [
    "purh.apostrophe",
    "purh.points_suspension",
    "purh.guillemets.droits",
    "R-ORTHO-LIGATURE-OE-001",
    "purh.guillemets.espace_apres_ouvrant",
    "purh.guillemets.espace_avant_fermant",
    "purh.espaces.avant_ponct_forte",
    "purh.espaces.avant_ponct_faible",
    "purh.espaces.double",
    "purh.civilite",
    "purh.siecles",
    "purh.ordinaux",
    "purh.tiret.double",
    "purh.abreviations.etc",
    "purh.pagination.espace",
    "purh.numero",
    "purh.abreviations.redoublement",
    "purh.nombres.milliers",
    "purh.tiret.incise",
]

EXPECTED_AUTOMATIC_RULE_IDS = {
    "purh.siecles",
    "purh.ordinaux",
    "purh.abreviations.etc",
    "purh.pagination.espace",
    "purh.numero",
    "purh.abreviations.redoublement",
}


def _fixture_cases() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(FIXTURES_DIR.glob("*.json"))
        if path.name != "_index.json"
    ]


def _document(text: str, *, attributes: dict | None = None) -> Document:
    return Document(
        document_id="doc-typo-deployment",
        source_path="fixture.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text, attributes=attributes or {})],
    )


def _representative_input(fixture: dict) -> str:
    cases = fixture["positive_cases"] or fixture["negative_cases"]
    return cases[0]["input"]


class OrthotypoDeploymentCharacterizationTests(unittest.TestCase):
    def test_exact_rule_order_and_final_auto_values(self) -> None:
        self.assertEqual([rule.rule_id for rule in TYPO_RULES], EXPECTED_RULE_IDS)
        self.assertEqual(
            {rule.rule_id for rule in TYPO_RULES if rule.auto},
            EXPECTED_AUTOMATIC_RULE_IDS,
        )
        self.assertFalse(next(rule for rule in TYPO_RULES if rule.rule_id == "purh.tiret.incise").auto)

    def test_each_currently_nonautomatic_rule_becomes_a_review_diagnostic(self) -> None:
        service = OrthotypoService()
        by_id = {item["rule_id"]: item for item in _fixture_cases()}
        for rule in TYPO_RULES:
            if rule.auto:
                continue
            with self.subTest(rule=rule.rule_id):
                source = _representative_input(by_id[rule.rule_id])
                corrected, transformations = service.apply(_document(source))
                diagnostics = service.analyze_unvalidated_rules(corrected)
                self.assertEqual(corrected.blocks[0].text, source)
                self.assertEqual(transformations, [])
                self.assertIn(rule.rule_id, {diagnostic.rule_id for diagnostic in diagnostics})

    def test_every_rule_is_silent_and_non_mutating_in_an_explicitly_protected_block(self) -> None:
        service = OrthotypoService()
        by_id = {item["rule_id"]: item for item in _fixture_cases()}
        for rule in TYPO_RULES:
            with self.subTest(rule=rule.rule_id):
                source = _representative_input(by_id[rule.rule_id])
                corrected, transformations = service.apply(
                    _document(source, attributes={"protected_zone": "citation"})
                )
                diagnostics = service.analyze_unvalidated_rules(corrected)
                self.assertEqual(corrected.blocks[0].text, source)
                self.assertEqual(transformations, [])
                self.assertEqual(diagnostics, [])

    def test_order_offsets_targets_and_second_pass_for_interacting_automatic_rules(self) -> None:
        source = "xviième siècle, etc... et n° 5 ; pp. 12"
        service = OrthotypoService()
        first, transformations = service.apply(_document(source))

        self.assertEqual(
            [item.rule_id for item in transformations],
            [
                "purh.siecles",
                "purh.abreviations.etc",
                "purh.pagination.espace",
                "purh.numero",
                "purh.abreviations.redoublement",
                "R-SO-001",
                "R-NO-001",
            ],
        )
        self.assertTrue(all(item.target_ref == "p1" for item in transformations))
        self.assertTrue(all(isinstance(item.attributes["offset_start"], int) for item in transformations))
        self.assertTrue(all(isinstance(item.attributes["offset_end"], int) for item in transformations))

        second, second_transformations = service.apply(first)
        self.assertEqual(second.blocks[0].text, first.blocks[0].text)
        self.assertEqual(second_transformations, [])


if __name__ == "__main__":
    unittest.main()
