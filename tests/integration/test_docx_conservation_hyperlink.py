from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io import ImporterRegistry
from purh_editorial.io.docx_exporter import DocxExporter
from tests.helpers.docx_factory import create_hyperlink_docx, create_minimal_template_docx


class DocxConservationHyperlinkTests(unittest.TestCase):
    """
    Matrice de conservation documentaire (docs/CONSERVATION_MATRIX.md) : ce test fixe
    le statut réel du texte de lien hypertexte à l'import/export - "conservé sans
    garantie" pour le texte, "non pris en charge" pour la cible du lien elle-même.
    """

    @staticmethod
    def _runtime_path(filename: str) -> Path:
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / filename


    def test_hyperlink_visible_text_is_preserved_on_import(self) -> None:
        docx_path = self._runtime_path(f"hyperlink_{uuid.uuid4().hex}.docx")
        create_hyperlink_docx(docx_path)
        document = ImporterRegistry().load_document(docx_path)

        full_text = "".join(span.text for span in document.blocks[0].inlines)
        self.assertIn("le site des PURH", full_text)
        self.assertIn("Voir", full_text)
        self.assertIn("details", full_text)

    def test_hyperlink_target_is_not_preserved_through_export(self) -> None:
        """
        Documente honnêtement une limite connue : le texte visible du lien survit à
        l'import (voir ci-dessus), mais la cible (URL) n'est capturée nulle part dans
        le modèle interne (InlineSpan n'a pas de champ dédié) et disparaît donc à
        l'export. Non pris en charge — pas une régression, un périmètre non couvert.
        """
        docx_path = self._runtime_path(f"hyperlink_{uuid.uuid4().hex}.docx")
        create_hyperlink_docx(docx_path)
        document = ImporterRegistry().load_document(docx_path)

        for block in document.blocks:
            for span in block.inlines:
                self.assertNotIn("href", span.attributes)
                self.assertNotIn("url", span.attributes)

        export_path = self._runtime_path(f"hyperlink_export_{uuid.uuid4().hex}.docx")
        template_path = create_minimal_template_docx(self._runtime_path(f"template_{uuid.uuid4().hex}.docx"))
        DocxExporter(template_path=template_path).export(document, export_path)
        with open(export_path, "rb") as f:
            exported_bytes = f.read()
        self.assertNotIn(b"purh.univ-rouen.fr", exported_bytes)


if __name__ == "__main__":
    unittest.main()
