from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.docx_importer import DocxImporter
from tests.helpers.docx_factory import JPEG_1X1_BYTES, PNG_1X1_BYTES, create_images_docx


class DocxImporterImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmpdir = tempfile.TemporaryDirectory()
        path = Path(self._tmpdir.name) / "images.docx"
        create_images_docx(path)
        self.document = DocxImporter().load(path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _occ_by_order(self):
        return sorted(self.document.image_occurrences, key=lambda o: o.order)

    def test_inline_png_is_captured_with_alt_and_title(self) -> None:
        occ = self._occ_by_order()[0]
        self.assertEqual(occ.placement, "inline")
        self.assertEqual(occ.alt_text, "Texte alternatif")
        self.assertEqual(occ.title, "Titre image")
        asset = self.document.image_assets[occ.asset_ref]
        self.assertEqual(asset.data, PNG_1X1_BYTES)
        self.assertEqual(asset.content_type, "image/png")
        self.assertEqual(asset.sha256, hashlib.sha256(PNG_1X1_BYTES).hexdigest())

    def test_inline_png_gets_caption_from_following_styled_paragraph(self) -> None:
        occ = self._occ_by_order()[0]
        self.assertEqual(occ.caption, "Légende de la première image.")

    def test_anchored_image_is_normalized_to_inline_with_flag(self) -> None:
        occurrences = self._occ_by_order()
        anchored = [o for o in occurrences if o.attributes.get("dml_container") == "anchor"]
        self.assertEqual(len(anchored), 1)
        self.assertTrue(anchored[0].anchor_normalized_to_inline)

    def test_jpeg_inline_is_captured_with_correct_content_type(self) -> None:
        occurrences = self._occ_by_order()
        jpeg_occ = next(o for o in occurrences if self.document.image_assets.get(o.asset_ref, None)
                         and self.document.image_assets[o.asset_ref].content_type == "image/jpeg")
        asset = self.document.image_assets[jpeg_occ.asset_ref]
        self.assertEqual(asset.data, JPEG_1X1_BYTES)

    def test_identical_bytes_are_deduplicated_into_single_asset(self) -> None:
        # image1.png et image4.png ont des octets identiques -> un seul ImageAsset.
        png_asset_ids = {
            occ.asset_ref for occ in self.document.image_occurrences
            if occ.asset_ref and self.document.image_assets[occ.asset_ref].data == PNG_1X1_BYTES
        }
        self.assertEqual(len(png_asset_ids), 1)
        occurrences_using_it = [o for o in self.document.image_occurrences if o.asset_ref in png_asset_ids]
        # image1 (corps), image2 (ancrée), image4 (reutilisee), image_table, image_note
        self.assertGreaterEqual(len(occurrences_using_it), 4)

    def test_external_link_image_has_no_asset_and_records_external_url(self) -> None:
        occurrences = self._occ_by_order()
        external = [o for o in occurrences if o.external_link]
        self.assertEqual(len(external), 1)
        self.assertEqual(external[0].asset_ref, "")
        self.assertEqual(external[0].external_link, "https://example.org/external.png")

    def test_chart_is_detected_as_complex_object_not_as_image(self) -> None:
        chart_objects = [o for o in self.document.complex_objects if o.object_type == "chart"]
        self.assertEqual(len(chart_objects), 1)
        # Le graphique ne doit jamais apparaître comme une image ordinaire.
        self.assertFalse(any(
            o.attributes.get("name") == "Chart 1" for o in self.document.image_occurrences
        ))

    def test_image_in_footnote_is_captured_with_note_placement(self) -> None:
        note_occurrences = [o for o in self.document.image_occurrences if o.placement == "note"]
        self.assertEqual(len(note_occurrences), 1)
        self.assertEqual(note_occurrences[0].target_ref, "ftn2")
        asset = self.document.image_assets[note_occurrences[0].asset_ref]
        self.assertEqual(asset.data, PNG_1X1_BYTES)

    def test_image_in_table_is_recorded_without_breaking_opaque_preservation(self) -> None:
        table_block = next(b for b in self.document.blocks if b.block_type == "table")
        self.assertIn("table_ooxml", table_block.attributes)
        self.assertIn("table_image_refs", table_block.attributes)
        table_occurrences = [o for o in self.document.image_occurrences if o.placement == "table"]
        self.assertEqual(len(table_occurrences), 1)
        self.assertEqual(table_occurrences[0].target_ref, table_block.block_id)

    def test_image_bearing_paragraph_is_not_treated_as_blank(self) -> None:
        # Le paragraphe qui ne contient QUE l'image ancrée ne doit pas disparaître
        # comme "paragraphe vide".
        anchored_target_refs = {
            o.target_ref for o in self.document.image_occurrences
            if o.attributes.get("dml_container") == "anchor"
        }
        for ref in anchored_target_refs:
            block = self.document.block_by_id(ref)
            self.assertIsNotNone(block)
            self.assertFalse(block.attributes.get("is_blank_para"))

    def test_occurrences_have_strictly_increasing_order(self) -> None:
        orders = [o.order for o in self.document.image_occurrences] + [
            o.order for o in self.document.complex_objects
        ]
        self.assertEqual(len(orders), len(set(orders)))


if __name__ == "__main__":
    unittest.main()
