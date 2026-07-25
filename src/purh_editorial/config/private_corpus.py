"""
Résolution du corpus éditorial privé (manuscrits réels, non publiés dans ce dépôt).

Voir docs/CORPUS_ET_FIXTURES.md pour la politique publique/privée complète. Ce module
ne contient et ne référence aucun contenu privé : uniquement la logique pour le
localiser sur la machine de l'utilisateur, s'il est installé.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_VAR = "PURH_PRIVATE_CORPUS_DIR"


class PrivateCorpusUnavailable(Exception):
    """Levée quand le corpus privé est requis mais introuvable ou invalide."""


@dataclass(frozen=True)
class PrivateCorpusPaths:
    """Chemins attendus sous la racine du corpus privé local.

    La structure attendue (voir docs/CORPUS_ET_FIXTURES.md) :
        <root>/sources/manuscripts_raw/
        <root>/sources/io_samples/
        <root>/sources/output_samples/
    """

    root: Path

    @property
    def manuscripts_raw(self) -> Path:
        return self.root / "sources" / "manuscripts_raw"

    @property
    def io_samples(self) -> Path:
        return self.root / "sources" / "io_samples"

    @property
    def output_samples(self) -> Path:
        return self.root / "sources" / "output_samples"


def resolve_private_corpus_dir() -> Path | None:
    """Retourne le dossier racine du corpus privé si la variable d'environnement
    PURH_PRIVATE_CORPUS_DIR est définie et pointe vers un dossier existant, sinon None."""
    value = os.environ.get(ENV_VAR)
    if not value:
        return None
    path = Path(value)
    if not path.is_dir():
        return None
    return path


def require_private_corpus() -> PrivateCorpusPaths:
    """Comme `resolve_private_corpus_dir`, mais lève PrivateCorpusUnavailable avec un
    message actionnable au lieu de retourner None. Réservé au code appelé uniquement
    quand la présence du corpus privé a déjà été vérifiée (ex. après un skip de test)."""
    path = resolve_private_corpus_dir()
    if path is None:
        raise PrivateCorpusUnavailable(
            f"Corpus privé introuvable : définissez la variable d'environnement "
            f"{ENV_VAR} vers la racine du corpus privé local "
            f"(voir docs/CORPUS_ET_FIXTURES.md, section « Installer le corpus privé »)."
        )
    return PrivateCorpusPaths(root=path)


def private_corpus_skip_reason() -> str | None:
    """Message à passer à unittest.skip(...) si le corpus privé est absent ; None si
    le corpus privé est disponible (le test ne doit alors pas être ignoré)."""
    if resolve_private_corpus_dir() is None:
        return (
            f"{ENV_VAR} non défini ou invalide : test sur corpus privé ignoré. "
            f"Voir docs/CORPUS_ET_FIXTURES.md pour installer le corpus localement."
        )
    return None
