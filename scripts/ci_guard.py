#!/usr/bin/env python
"""
Garde-fou de confidentialité et de terminologie, exécuté en CI (voir
.github/workflows/ci.yml) et localement avant tout commit sensible.

Échoue si :
- un fichier privé (DOCX/PDF/EPUB/ZIP/INDD non explicitement autorisé) est suivi par
  Git sous sources/, fixtures/ ou exports/ ;
- un fichier de fixture se présente comme normatif ("gold"/"or") sans satisfaire le
  schéma de fixtures/orthotypography_gold/ (validated=true + validation_source réelle) ;
- un fichier `.env` (secrets réels) ou une clé privée PEM est suivi par Git ;
- un fichier suivi contient une valeur qui ressemble à une clé API (Groq, OpenAI,
  Anthropic, Gemini/Google) ou un autre secret courant.

Voir docs/CORPUS_ET_FIXTURES.md pour la politique complète.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Noms de fichiers jamais suivis (secrets réels). `.env.example` reste autorisé.
_FORBIDDEN_FILENAMES = {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
_FORBIDDEN_SUFFIXES = {".pem", ".pfx", ".p12", ".key"}

# Motifs de secrets courants. Chaque motif capture la valeur dans le groupe 1
# pour permettre de la tronquer avant affichage.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("clé Groq", re.compile(r"\b(gsk_[A-Za-z0-9]{20,})\b")),
    ("clé OpenAI", re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b")),
    ("clé Anthropic", re.compile(r"\b(sk-ant-[A-Za-z0-9\-_]{20,})\b")),
    ("clé Gemini/Google", re.compile(r"\b(AIza[A-Za-z0-9_\-]{35})\b")),
    ("clé privée PEM", re.compile(r"(-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----)")),
]

# Fichiers dont le contenu est fait de placeholders et ne doit pas être scanné
# pour de "vraies" valeurs (ils contiennent volontairement des mots comme "key").
_SECRET_SCAN_ALLOWLIST = {".env.example"}

# Extensions binaires ou volumineuses à ne pas tenter de lire comme texte.
_SECRET_SCAN_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico",
    ".docx", ".pdf", ".epub", ".zip", ".dotm", ".dotx", ".indd", ".idml",
    ".woff", ".woff2", ".ttf", ".otf",
}


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}…{value[-2:]} ({len(value)} car.)"

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


def check_no_secrets_tracked(tracked: list[str]) -> list[str]:
    errors = []
    for path in tracked:
        name = Path(path).name
        suffix = Path(path).suffix.lower()
        if name in _FORBIDDEN_FILENAMES:
            errors.append(f"fichier de secret suivi : {path} (nom interdit : {name})")
            continue
        if suffix in _FORBIDDEN_SUFFIXES:
            errors.append(f"fichier de secret suivi : {path} (extension interdite : {suffix})")
            continue
        if name in _SECRET_SCAN_ALLOWLIST or suffix in _SECRET_SCAN_SKIP_SUFFIXES:
            continue
        full_path = ROOT / path
        try:
            content = full_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in _SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                errors.append(
                    f"valeur ressemblant à une {label} détectée dans {path} : {_mask(match.group(1))}"
                )
    return errors


def main() -> int:
    tracked = _tracked_files()
    errors: list[str] = []
    errors.extend(check_no_private_binaries(tracked))
    errors.extend(check_gold_fixtures_are_validated())
    errors.extend(check_characterization_fixtures_do_not_claim_gold())
    errors.extend(check_no_secrets_tracked(tracked))

    if errors:
        print("Échec du garde-fou de confidentialité/terminologie :", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Garde-fou de confidentialité/terminologie : OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
