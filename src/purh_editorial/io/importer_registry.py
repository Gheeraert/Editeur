from __future__ import annotations

from pathlib import Path

from purh_editorial.io.docx_importer import DocxImporter
from purh_editorial.io.importer_base import DocumentImporter, UnsupportedFormatError
from purh_editorial.io.tei_xml_importer import TeiXmlImporter
from purh_editorial.io.txt_importer import TxtImporter
from purh_editorial.model import Document


class ImporterRegistry:
    def __init__(self, importers: list[DocumentImporter] | None = None) -> None:
        self.importers = importers or [DocxImporter(), TeiXmlImporter(), TxtImporter()]

    def load_document(self, path: Path) -> Document:
        for importer in self.importers:
            if importer.supports(path):
                return importer.load(path)
        supported = sorted({ext for importer in self.importers for ext in importer.supported_extensions})
        raise UnsupportedFormatError(
            f"Format non pris en charge pour {path}. Formats supportés: {', '.join(supported)}"
        )
