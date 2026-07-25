from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.docx_exporter import DocxExporter
from purh_editorial.io.docx_importer import DocxImporter
from tests.helpers.docx_factory import (
    JPEG_1X1_BYTES, PNG_1X1_BYTES, create_images_docx, create_minimal_template_docx,
)


class DocxExporterImagesRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self._tmpdir.name)
        source_path = tmp / "images.docx"
        create_images_docx(source_path)
        self.document = DocxImporter().load(source_path)

        template_path = tmp / "template.docx"
        create_minimal_template_docx(template_path)
        output_path = tmp / "out.docx"
        DocxExporter(template_path=template_path).export(self.document, output_path)
        self.output_path = output_path
        self.reimported = DocxImporter().load(output_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_output_docx_has_well_formed_core_parts(self) -> None:
        with zipfile.ZipFile(self.output_path) as z:
            for name in ("word/document.xml", "word/footnotes.xml", "[Content_Types].xml"):
                ET.fromstring(z.read(name))  # ne doit pas lever

    def test_inline_png_survives_with_identical_bytes(self) -> None:
        first_pass_occ = sorted(self.document.image_occurrences, key=lambda o: o.order)[0]
        original_bytes = self.document.image_assets[first_pass_occ.asset_ref].data
        self.assertEqual(original_bytes, PNG_1X1_BYTES)

        reimported_pngs = [
            self.reimported.image_assets[o.asset_ref].data
            for o in self.reimported.image_occurrences
            if o.asset_ref and self.reimported.image_assets[o.asset_ref].content_type == "image/png"
        ]
        self.assertIn(PNG_1X1_BYTES, reimported_pngs)

    def test_jpeg_survives_with_identical_bytes(self) -> None:
        reimported_jpegs = [
            self.reimported.image_assets[o.asset_ref].data
            for o in self.reimported.image_occurrences
            if o.asset_ref and self.reimported.image_assets[o.asset_ref].content_type == "image/jpeg"
        ]
        self.assertIn(JPEG_1X1_BYTES, reimported_jpegs)

    def test_anchored_image_survives_normalized_as_inline(self) -> None:
        # L'export normalise systematiquement en inline (option 2 de la Partie D7).
        png_count_after = sum(
            1 for o in self.reimported.image_occurrences
            if o.asset_ref and self.reimported.image_assets[o.asset_ref].data == PNG_1X1_BYTES
        )
        self.assertGreaterEqual(png_count_after, 3)  # corps, reutilisee, table, note (au moins 3)

    def test_image_in_note_survives(self) -> None:
        note_occurrences = [o for o in self.reimported.image_occurrences if o.placement == "note"]
        self.assertEqual(len(note_occurrences), 1)
        asset = self.reimported.image_assets[note_occurrences[0].asset_ref]
        self.assertEqual(asset.data, PNG_1X1_BYTES)

    def test_image_in_table_survives_via_rid_remap(self) -> None:
        table_block = next(b for b in self.reimported.blocks if b.block_type == "table")
        table_occurrences = [o for o in self.reimported.image_occurrences if o.placement == "table"]
        self.assertEqual(len(table_occurrences), 1)
        self.assertEqual(table_occurrences[0].target_ref, table_block.block_id)
        asset = self.reimported.image_assets[table_occurrences[0].asset_ref]
        self.assertEqual(asset.data, PNG_1X1_BYTES)

    def test_external_link_image_is_not_falsely_claimed_as_embedded(self) -> None:
        # Rien a reinjecter (pas d'octets) : elle ne doit pas reapparaitre comme
        # une image incorporee dans le document reexporte.
        embedded_png_like = [
            o for o in self.reimported.image_occurrences
            if o.external_link == "https://example.org/external.png"
        ]
        self.assertEqual(embedded_png_like, [])

    def test_second_export_pass_is_stable_on_image_count(self) -> None:
        tmp = Path(self._tmpdir.name)
        template_path = tmp / "template.docx"
        second_output = tmp / "out2.docx"
        DocxExporter(template_path=template_path).export(self.reimported, second_output)
        twice_reimported = DocxImporter().load(second_output)
        self.assertEqual(
            len(self.reimported.image_occurrences),
            len(twice_reimported.image_occurrences),
        )


if __name__ == "__main__":
    unittest.main()
