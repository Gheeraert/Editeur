#!/usr/bin/env python
"""
Garde-fou de confidentialité et de terminologie, exécuté en CI (voir
.github/workflows/ci.yml) et localement avant tout commit sensible.

Échoue si :
- un fichier privé (DOCX/PDF/EPUB/ZIP/INDD non explicitement autorisé) est suivi par
  Git sous sources/, fixtures/ ou exports/ ;
- un fichier de fixture se présente comme normatif ("gold"/"or") sans satisfaire le
  schéma de fixtures/orthotypography_gold/ (validated=true + validation_source réelle).

Voir docs/CORPUS_ET_FIXTURES.md pour la politique complète.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Extensions binaires jamais suivies sous sources/ ou exports/ dans le dépôt public.
_FORBIDDEN_EXTENSIONS = {".docx", ".pdf", ".epub", ".zip", ".indd", ".idml", ".dotm"}

# Chemins où un README générique est le seul contenu autorisé.
_PRIVATE_ONLY_PREFIXES = ("sources/", "exports/")

# Fichiers explicitement autorisés malgré leur extension (aucun aujourd'hui).
_ALLOWLIST: set[str] = set()


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def check_no_private_binaries(tracked: list[str]) -> list[str]:
    errors = []
    for path in tracked:
        if path in _ALLOWLIST:
            continue
        if not path.startswith(_PRIVATE_ONLY_PREFIXES):
            continue
        suffix = Path(path).suffix.lower()
        if suffix in _FORBIDDEN_EXTENSIONS:
            errors.append(f"fichier privé suivi publiquement : {path}")
    return errors


def check_gold_fixtures_are_validated() -> list[str]:
    errors = []
    gold_dir = ROOT / "fixtures" / "orthotypography_gold"
    if not gold_dir.is_dir():
        return errors
    for path in gold_dir.glob("*.json"):
        if path.name == "_index.json":
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        for case in data.get("gold_cases", []):
            if not case.get("validated"):
                errors.append(f"{path.relative_to(ROOT)}: cas non validated=true présent dans le corpus d'or")
                continue
            source = case.get("validation_source") or {}
            if source.get("type") not in {"guide_purh", "editorial_copy", "human_validation"}:
                errors.append(
                    f"{path.relative_to(ROOT)}: validation_source.type invalide ({source.get('type')!r})"
                )
            if not source.get("reference"):
                errors.append(f"{path.relative_to(ROOT)}: validation_source.reference manquante")
    return errors


def check_characterization_fixtures_do_not_claim_gold() -> list[str]:
    errors = []
    char_dir = ROOT / "fixtures" / "orthotypography_characterization"
    if not char_dir.is_dir():
        return errors
    for path in char_dir.glob("*.json"):
        if path.name == "_index.json":
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        for case in data.get("positive_cases", []) + data.get("negative_cases", []):
            if "validated" in case or "validation_source" in case:
                errors.append(
                    f"{path.relative_to(ROOT)}: un cas de caractérisation ne doit jamais porter "
                    f"validated/validation_source (réservé au corpus d'or normatif)"
                )
    return errors


def main() -> int:
    tracked = _tracked_files()
    errors: list[str] = []
    errors.extend(check_no_private_binaries(tracked))
    errors.extend(check_gold_fixtures_are_validated())
    errors.extend(check_characterization_fixtures_do_not_claim_gold())

    if errors:
        print("Échec du garde-fou de confidentialité/terminologie :", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Garde-fou de confidentialité/terminologie : OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
