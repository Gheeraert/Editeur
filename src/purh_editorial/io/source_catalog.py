from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {".docx", ".txt", ".md", ".xml"}


def discover_source_documents(sources_dir: Path) -> list[Path]:
    if not sources_dir.exists():
        return []
    paths: list[Path] = []
    for path in sources_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        paths.append(path)
    return sorted(paths)
