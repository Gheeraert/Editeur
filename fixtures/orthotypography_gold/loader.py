"""Chargeur du corpus d'or normatif. Voir SCHEMA.md pour le format et
docs/CORPUS_ET_FIXTURES.md pour la politique. Ne contient aucune donnée : uniquement
la logique de lecture et de validation minimale du schéma."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

GOLD_DIR = Path(__file__).resolve().parent
_VALID_SOURCE_TYPES = {"guide_purh", "editorial_copy", "human_validation"}


class InvalidGoldCase(Exception):
    """Levée quand un cas ne satisfait pas le schéma normatif minimal."""


@dataclass(frozen=True)
class GoldCase:
    rule_id: str
    input: str
    expected_output: str
    validation_source_type: str
    validation_source_reference: str


def _validate_case(rule_id: str, raw: dict) -> GoldCase:
    if not raw.get("validated"):
        raise InvalidGoldCase(f"{rule_id}: cas non marqué validated=true, ignoré par construction.")
    source = raw.get("validation_source") or {}
    source_type = source.get("type")
    if source_type not in _VALID_SOURCE_TYPES:
        raise InvalidGoldCase(
            f"{rule_id}: validation_source.type invalide ou absent ({source_type!r}), "
            f"attendu l'un de {sorted(_VALID_SOURCE_TYPES)}."
        )
    if not source.get("reference"):
        raise InvalidGoldCase(f"{rule_id}: validation_source.reference manquante.")
    return GoldCase(
        rule_id=rule_id,
        input=raw["input"],
        expected_output=raw["expected_output"],
        validation_source_type=source_type,
        validation_source_reference=source["reference"],
    )


def load_gold_cases(directory: Path | None = None) -> list[GoldCase]:
    """Charge tous les cas normatifs valides (validated=true, source renseignée) des
    fichiers *.json du dossier donné (par défaut ce dossier). Un cas qui ne satisfait
    pas le schéma minimal est ignoré silencieusement plutôt que planté : un corpus d'or
    encore incomplet ne doit jamais faire échouer la CI."""
    root = directory or GOLD_DIR
    cases: list[GoldCase] = []
    for path in sorted(root.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        rule_id = data.get("rule_id", path.stem)
        for raw_case in data.get("gold_cases", []):
            try:
                cases.append(_validate_case(rule_id, raw_case))
            except InvalidGoldCase:
                continue
    return cases
