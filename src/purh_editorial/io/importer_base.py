from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from purh_editorial.model import Document


class ImportErrorBase(RuntimeError):
    """Base class for ingestion-related errors."""


class UnsupportedFormatError(ImportErrorBase):
    pass


class DocumentImporter(ABC):
    supported_extensions: tuple[str, ...] = ()

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def load(self, path: Path) -> Document:
        raise NotImplementedError
