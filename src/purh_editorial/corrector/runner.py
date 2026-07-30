from __future__ import annotations

import shutil
from pathlib import Path

from purh_editorial.corrector.word_document import correct_word_copy


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
    return correct_word_copy(destination_resolved)

