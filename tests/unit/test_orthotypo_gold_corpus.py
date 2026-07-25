from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.services.orthotypo_service import TYPO_RULES

FIXTURES_DIR = ROOT / "fixtures" / "orthotypography"

_RULES_BY_ID = {rule.rule_id: rule for rule in TYPO_RULES}


def _load_fixtures() -> list[dict]:
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        if path.name == "_index.json":
            continue
        with path.open(encoding="utf-8") as f:
            fixtures.append(json.load(f))
    return fixtures


class OrthotypoGoldCorpusTests(unittest.TestCase):
    """
    Corpus d'or (Phase 5) : cas positifs et négatifs extraits pour la plupart
    directement de manuscrits réels (H&P2, Iphigénie, dissimuler — voir le champ
    "origin" de chaque cas), plutôt que fabriqués. Un cas par TypoRule est appliqué
    isolément (comme lors de son extraction) et comparé à la sortie attendue.
    """

    def test_fixtures_directory_covers_all_typo_rules(self) -> None:
        fixture_rule_ids = {f["rule_id"] for f in _load_fixtures()}
        code_rule_ids = set(_RULES_BY_ID)
        self.assertEqual(
            fixture_rule_ids,
            code_rule_ids,
            "Le corpus d'or doit couvrir exactement les TypoRule de OrthotypoService.",
        )

    def test_positive_cases(self) -> None:
        for fixture in _load_fixtures():
            rule = _RULES_BY_ID[fixture["rule_id"]]
            for case in fixture["positive_cases"]:
                with self.subTest(rule=fixture["rule_id"], origin=case["origin"]):
                    self.assertEqual(rule.apply(case["input"]), case["expected_output"])

    def test_negative_cases(self) -> None:
        for fixture in _load_fixtures():
            rule = _RULES_BY_ID[fixture["rule_id"]]
            for case in fixture["negative_cases"]:
                with self.subTest(rule=fixture["rule_id"], origin=case["origin"]):
                    self.assertEqual(rule.apply(case["input"]), case["expected_output"])

    def test_known_contradiction_cases_document_current_behavior(self) -> None:
        # Ces cas ne sont pas des tests de correction : ils figent la sortie actuelle
        # (contradictoire avec la pratique éditoriale réelle ou le guide PURH) pour
        # qu'un futur correctif de la règle fasse échouer ce test de façon visible,
        # plutôt que de dériver silencieusement une deuxième fois.
        for fixture in _load_fixtures():
            contradiction = fixture.get("known_contradiction")
            if not contradiction:
                continue
            rule = _RULES_BY_ID[fixture["rule_id"]]
            for case in contradiction["cases"]:
                with self.subTest(rule=fixture["rule_id"], origin=case["origin"]):
                    self.assertEqual(rule.apply(case["input"]), case["current_output"])


if __name__ == "__main__":
    unittest.main()
