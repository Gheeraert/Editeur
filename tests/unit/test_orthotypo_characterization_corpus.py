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
from purh_editorial.services.orthotypo_service import TYPO_RULES
from purh_editorial.services.orthotypo_service import OrthotypoService

FIXTURES_DIR = ROOT / "fixtures" / "orthotypography_characterization"

_KNOWN_RULE_IDS = {rule.rule_id for rule in TYPO_RULES}


def _apply_via_pipeline(text: str) -> str:
    """Applique le pipeline OrthotypoService complet (pas TypoRule.apply en isolation)
    pour que le corpus caractérise fidèlement le comportement réel du logiciel, y
    compris le fait qu'une règle marquée auto=False (ex. purh.tiret.incise) ne
    corrige plus rien automatiquement."""
    document = Document(
        document_id="doc-characterization",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    corrected, _transformations = OrthotypoService().apply(document)
    return corrected.blocks[0].text


def _load_fixtures() -> list[dict]:
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        if path.name == "_index.json":
            continue
        with path.open(encoding="utf-8") as f:
            fixtures.append(json.load(f))
    return fixtures


class OrthotypoCharacterizationCorpusTests(unittest.TestCase):
    """
    Corpus de caractérisation (Phase 5, corrigé lors de la passe d'assainissement) :
    enregistre ce que OrthotypoService produit *actuellement*, avec des cas
    exclusivement synthétiques (aucun extrait de manuscrit réel — voir
    docs/CORPUS_ET_FIXTURES.md pour la distinction avec un corpus d'or normatif).

    Ce n'est PAS une preuve de correction éditoriale : voir le champ "automatic" et
    la note de fixtures/orthotypography_characterization/purh_tiret_incise.json pour un
    exemple de comportement volontairement figé bien que connu comme incertain.
    """

    def test_fixtures_directory_covers_all_typo_rules(self) -> None:
        fixture_rule_ids = {f["rule_id"] for f in _load_fixtures()}
        self.assertEqual(
            fixture_rule_ids,
            _KNOWN_RULE_IDS,
            "Le corpus de caractérisation doit couvrir exactement les TypoRule de OrthotypoService.",
        )

    def test_automatic_flag_is_not_a_claim_of_current_purh_validation(self) -> None:
        rules_by_id = {rule.rule_id: rule for rule in TYPO_RULES}
        for fixture in _load_fixtures():
            with self.subTest(rule=fixture["rule_id"]):
                self.assertIn(fixture["automatic"], {True, False})
                self.assertIn(fixture["rule_id"], rules_by_id)

    def test_positive_cases_via_full_pipeline(self) -> None:
        for fixture in _load_fixtures():
            for case in fixture["positive_cases"]:
                with self.subTest(rule=fixture["rule_id"], input=case["input"]):
                    rule = next(rule for rule in TYPO_RULES if rule.rule_id == fixture["rule_id"])
                    expected = case["expected_output"] if rule.auto else case["input"]
                    self.assertEqual(_apply_via_pipeline(case["input"]), expected)

    def test_negative_cases_via_full_pipeline(self) -> None:
        for fixture in _load_fixtures():
            for case in fixture["negative_cases"]:
                with self.subTest(rule=fixture["rule_id"], input=case["input"]):
                    expected = case["expected_output"]
                    if fixture["rule_id"] == "purh.siecles":
                        # The fixture's apostrophe normalization is no longer automatic.
                        expected = case["input"]
                    self.assertEqual(_apply_via_pipeline(case["input"]), expected)

    def test_no_case_claims_to_be_a_normative_gold_case(self) -> None:
        # Un cas de caractérisation ne doit jamais porter les champs du schéma normatif
        # (voir fixtures/orthotypography_gold/SCHEMA.md) : "validated" ou
        # "validation_source" signaleraient à tort une validation indépendante du code.
        for fixture in _load_fixtures():
            for case in fixture["positive_cases"] + fixture["negative_cases"]:
                with self.subTest(rule=fixture["rule_id"]):
                    self.assertNotIn("validated", case)
                    self.assertNotIn("validation_source", case)
                    self.assertNotIn("gold", case.get("origin", "").lower())


if __name__ == "__main__":
    unittest.main()
