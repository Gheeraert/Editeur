from __future__ import annotations

import shutil
from pathlib import Path

from purh_editorial.corrector.word_document import correct_word_copy


DETERMINISTIC_RULE_IDS = (
    "purh.apostrophe",
    "purh.points_suspension",
    "R-ORTHO-LIGATURE-OE-001",
    "purh.guillemets.espace_apres_ouvrant",
    "purh.guillemets.espace_avant_fermant",
    "purh.espaces.avant_ponct_forte",
    "purh.espaces.avant_ponct_faible",
    "purh.espaces.double",
    "purh.civilite",
    "purh.siecles",
    "purh.ordinaux",
    "purh.abreviations.etc",
    "purh.pagination.espace",
    "purh.numero",
    "purh.abreviations.redoublement",
    "purh.nombres.milliers",
    "R-SO-001",
    "R-NO-001",
    "purh.note.espace_initiale",
    "purh.note.espace_op_cit",
    "purh.note.espace_sans_lieu_date",
    "purh.biblio.pagination_nnbsp",
    "purh.biblio.numero_nnbsp",
    "structure.frontmatter.abstract",
    "structure.frontmatter.keywords",
    "structure.frontmatter.acknowledgment",
    "R-TI-001",
    "R-AN-002",
    "R-AN-003",
    "structure.frontmatter.circuit_breaker",
)

HEURISTIC_RULE_IDS = (
    "purh.guillemets.droits",
    "purh.tiret.double",
    "purh.tiret.incise",
    "R-GQ-004",
    "purh.note.majuscule_initiale",
    "purh.note.abreviation_latine",
    "purh.note.ponctuation_finale",
    "R-AN-004",
    "R-AN-005",
    "structure.bibliography.section.start",
    "structure.bibliography.section.end",
    "structure.bibliography.item.promote",
    "bibliography.entry.detect",
    "purh.biblio.ponctuation_finale",
    "structure.source_style.heading",
    "structure.allcaps.heading",
    "structure.bold.heading",
    "structure.italic.author",
    "structure.italic.heading",
    "structure.epigraph.heuristic",
    "structure.bibliography.section",
    "structure.bibliography.heuristic",
    "structure.indent.quote",
    "structure.quote.guillemets",
    "structure.heading.heuristic",
    "R-STRUCT-HEADING-001",
    "structure.lineated.blank_bounded.merge",
    "structure.lineated.short_sequence.merge",
    "R-CI-POETRY-001",
    "structure.lineated.group.annotate",
    "structure.lineated.stanza.merge",
)

RULE_IDS = DETERMINISTIC_RULE_IDS + HEURISTIC_RULE_IDS


def correct_docx(input_path: Path, output_path: Path) -> dict[str, int]:
    source = Path(input_path)
    destination = Path(output_path)

    if not source.is_file():
        raise FileNotFoundError(f"Document d'entrée introuvable : {source}")
    if source.suffix.lower() != ".docx":
        raise ValueError("Le document d'entrée doit porter l'extension .docx.")

    source_resolved = source.resolve()
    destination_resolved = destination.resolve()
    if source_resolved == destination_resolved:
        raise ValueError("Les chemins d'entrée et de sortie doivent être différents.")
    if destination.exists():
        raise FileExistsError(f"Le fichier de sortie existe déjà : {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return correct_word_copy(destination_resolved, RULE_IDS)
