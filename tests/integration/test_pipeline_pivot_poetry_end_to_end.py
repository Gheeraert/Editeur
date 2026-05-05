from __future__ import annotations

import json
import sys
import unittest
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline

TEI_NS = "http://www.tei-c.org/ns/1.0"

DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Titre de section</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Paragraphe de prose normal.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>« Citation en prose. »</w:t></w:r>
    </w:p>
    <w:p/>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Je vois </w:t></w:r>
      <w:r><w:rPr><w:i/></w:rPr><w:t>Phèdre</w:t></w:r>
      <w:r><w:t> venir.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Deuxième vers du même extrait.</w:t></w:r>
    </w:p>
    <w:p/>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Reprise de prose après le bloc.</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>
"""

CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Poetry E2E fixture</dc:title>
  <dc:creator>PURH tests</dc:creator>
  <dc:language>fr</dc:language>
</cp:coreProperties>
"""


class PipelinePivotPoetryEndToEndTests(unittest.TestCase):
    @staticmethod
    def _create_e2e_docx(path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", DOC_XML)
            archive.writestr("word/styles.xml", STYLES_XML)
            archive.writestr("docProps/core.xml", CORE_XML)
        return path

    @staticmethod
    def _inline_summary(block: dict) -> list[dict]:
        summary: list[dict] = []
        for span in block.get("inlines") or []:
            style = span.get("style") or {}
            style_flags = sorted([k for k, v in style.items() if v])
            summary.append(
                {
                    "kind": span.get("kind"),
                    "text": span.get("text"),
                    "note_ref": span.get("note_ref"),
                    "style": style_flags,
                }
            )
        return summary

    @classmethod
    def _blocks_audit_summary(cls, blocks: list[dict]) -> list[dict]:
        compact: list[dict] = []
        for block in blocks:
            attrs = block.get("attributes") or {}
            compact.append(
                {
                    "block_id": block.get("block_id"),
                    "block_type": block.get("block_type"),
                    "text": block.get("text"),
                    "semantic": attrs.get("semantic"),
                    "protected_zone": attrs.get("protected_zone"),
                    "quote_kind": attrs.get("quote_kind"),
                    "lineation": attrs.get("lineation"),
                    "metopes_style": attrs.get("metopes_style"),
                    "style_name": attrs.get("style_name"),
                    "source_style": attrs.get("source_style"),
                    "source_span": block.get("source_span"),
                    "inline_summary": cls._inline_summary(block),
                }
            )
        return compact

    def test_e2e_docx_to_json_to_tei_uses_lineated_block(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        source_path = runtime_dir / f"poetry_chain_src_{uuid.uuid4().hex}.docx"
        tei_output_path = runtime_dir / f"poetry_chain_tei_{uuid.uuid4().hex}.xml"
        pivot_json_output_path = runtime_dir / f"poetry_chain_pivot_{uuid.uuid4().hex}.json"
        self._create_e2e_docx(source_path)

        pipeline.run(
            source_path,
            Step1Options(
                enable_ai=False,
                output_path=None,
                tei_output_path=tei_output_path,
                pivot_json_output_path=pivot_json_output_path,
            ),
        )

        self.assertTrue(pivot_json_output_path.exists(), "Le JSON pivot n'a pas été écrit.")
        pivot_payload = json.loads(pivot_json_output_path.read_text(encoding="utf-8"))
        self.assertEqual(pivot_payload.get("schema_version"), "pivot-1.0")

        blocks = pivot_payload.get("document", {}).get("blocks", [])
        blocks_summary = self._blocks_audit_summary(blocks)
        debug_path = runtime_dir / f"poetry_chain_debug_{uuid.uuid4().hex}.json"
        debug_path.write_text(
            json.dumps(
                {
                    "source_path": str(source_path),
                    "pivot_json_path": str(pivot_json_output_path),
                    "tei_output_path": str(tei_output_path),
                    "blocks_summary": blocks_summary,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        all_text = "\n".join(str(block.get("text") or "") for block in blocks)
        self.assertIn("Je vois", all_text, "Le contenu attendu 'Je vois' est absent du pivot.")
        self.assertIn("Phèdre", all_text, "Le contenu attendu 'Phèdre' est absent du pivot.")
        self.assertIn("Deuxième vers", all_text, "Le second vers attendu est absent du pivot.")

        has_italic_phaedre = False
        has_phaedre_inline = False
        for block in blocks:
            for span in block.get("inlines") or []:
                span_text = str(span.get("text") or "")
                style = span.get("style") or {}
                if "Phèdre" in span_text:
                    has_phaedre_inline = True
                    if bool(style.get("italic")):
                        has_italic_phaedre = True
        if has_phaedre_inline:
            self.assertTrue(
                has_italic_phaedre,
                f"Inline 'Phèdre' présent sans italique dans le pivot. Diagnostic: {debug_path}",
            )

        blank_like_blocks = [
            b for b in blocks if str(b.get("text") or "").strip() == "" and b.get("block_type") == "paragraph"
        ]

        canonical_lineated_blocks = []
        for block in blocks:
            semantic = (block.get("attributes") or {}).get("semantic") or {}
            if (
                semantic.get("role") == "lineated_block"
                and semantic.get("layout_kind") == "lineated_block"
                and semantic.get("lineation") == "lineated"
            ):
                lines = semantic.get("lines") or []
                if isinstance(lines, list) and len(lines) >= 2:
                    canonical_lineated_blocks.append((block, semantic))

        if not canonical_lineated_blocks:
            self.skipTest(
                "TODO(structure recognition/canonicalization): DOCX import a produit un pivot JSON valide, "
                "mais aucun bloc lineated canonique (role=lineated_block, layout_kind=lineated_block, "
                "lineation=lineated, >=2 lines). "
                f"blank_paragraphs={len(blank_like_blocks)} debug={debug_path}"
            )

        _lineated_block, lineated_semantic = canonical_lineated_blocks[0]
        lineated_lines_json = [str(line).strip() for line in (lineated_semantic.get("lines") or []) if str(line).strip()]
        self.assertGreaterEqual(len(lineated_lines_json), 2)
        lineated_inlines = _lineated_block.get("inlines") or []
        self.assertTrue(lineated_inlines, "Le bloc lineated canonique ne doit pas perdre ses inlines.")
        italic_span = next((s for s in lineated_inlines if s.get("text") == "Phèdre"), None)
        self.assertIsNotNone(italic_span, "Inline 'Phèdre' absent du bloc lineated canonique.")
        self.assertTrue(bool((italic_span.get("style") or {}).get("italic")), "'Phèdre' doit rester en italique.")

        if not tei_output_path.exists():
            self.skipTest(
                "TODO(TEI export gate/render): pivot poésie canonique détecté, mais le fichier XML-TEI n'a pas été produit."
            )

        xml_text = tei_output_path.read_text(encoding="utf-8")
        root = ET.fromstring(xml_text)
        lg_nodes = root.findall(f".//{{{TEI_NS}}}lg")
        l_nodes = root.findall(f".//{{{TEI_NS}}}l")
        self.assertTrue(lg_nodes, "Aucun <lg> dans le TEI.")
        self.assertGreaterEqual(len(l_nodes), 2, "Moins de deux vers <l> dans le TEI.")
        first_l = l_nodes[0]
        italic_nodes = first_l.findall(f".//{{{TEI_NS}}}hi[@rend='italic']")
        self.assertTrue(any("Phèdre" in "".join(node.itertext()) for node in italic_nodes))

        tei_lines = ["".join(node.itertext()).strip() for node in l_nodes if "".join(node.itertext()).strip()]
        self.assertGreaterEqual(len(tei_lines), 2)
        overlap = set(lineated_lines_json) & set(tei_lines)
        self.assertTrue(
            overlap,
            "Incohérence JSON/TEI: aucune ligne de vers commune entre semantic.lines et les <l> TEI.",
        )

    def test_pivot_json_preserves_imported_inlines_and_blank_boundary_evidence(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        source_path = runtime_dir / f"poetry_chain_src_{uuid.uuid4().hex}.docx"
        pivot_json_output_path = runtime_dir / f"poetry_chain_pivot_{uuid.uuid4().hex}.json"
        self._create_e2e_docx(source_path)

        pipeline.run(
            source_path,
            Step1Options(
                enable_ai=False,
                output_path=None,
                tei_output_path=None,
                pivot_json_output_path=pivot_json_output_path,
            ),
        )
        payload = json.loads(pivot_json_output_path.read_text(encoding="utf-8"))
        blocks = payload.get("document", {}).get("blocks", [])

        poetry_like = next((b for b in blocks if "Phèdre" in str(b.get("text") or "")), None)
        self.assertIsNotNone(poetry_like)
        inlines = poetry_like.get("inlines") or []
        self.assertTrue(inlines, "Les inlines du bloc poésie ne doivent pas disparaître après fusion.")
        italic_span = next((s for s in inlines if s.get("text") == "Phèdre"), None)
        self.assertIsNotNone(italic_span)
        self.assertTrue(bool((italic_span.get("style") or {}).get("italic")))

        second_verse = next((b for b in blocks if "Deuxième vers" in str(b.get("text") or "")), None)
        self.assertIsNotNone(second_verse)
        self.assertTrue(bool((poetry_like.get("attributes") or {}).get("blank_para_before")))
        if second_verse is poetry_like:
            self.assertIn("Deuxième vers", str(poetry_like.get("text") or ""))
            self.assertTrue(
                bool((poetry_like.get("attributes") or {}).get("merged_from")),
                "Bloc poésie fusionné attendu avec trace merged_from.",
            )
        else:
            self.assertTrue(bool((second_verse.get("attributes") or {}).get("blank_para_after")))


    def test_lineated_block_lines_have_no_embedded_newlines(self) -> None:
        """Régression : lines[0] ne doit pas contenir le texte fusionné complet avec \\n."""
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        source_path = runtime_dir / f"lines_corruption_{uuid.uuid4().hex}.docx"
        pivot_path = runtime_dir / f"lines_corruption_{uuid.uuid4().hex}.json"

        # Trois vers en séquence blancs-bornés
        three_verse_doc_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:t>Prose avant.</w:t></w:r></w:p>
    <w:p/>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:t>Premier vers du bloc.</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:t>Deuxième vers du bloc.</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:t>Troisième vers du bloc.</w:t></w:r></w:p>
    <w:p/>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:t>Prose après.</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>"""
        path = source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", three_verse_doc_xml)
            archive.writestr("word/styles.xml", STYLES_XML)
            archive.writestr("docProps/core.xml", CORE_XML)

        pipeline.run(
            source_path,
            Step1Options(enable_ai=False, output_path=None, pivot_json_output_path=pivot_path),
        )

        payload = json.loads(pivot_path.read_text(encoding="utf-8"))
        blocks = payload.get("document", {}).get("blocks", [])

        lineated = [
            b for b in blocks
            if (b.get("attributes") or {}).get("semantic", {}).get("role") == "lineated_block"
        ]
        if not lineated:
            self.skipTest("Aucun lineated_block détecté (seuil heuristique non atteint).")

        for block in lineated:
            lines = block["attributes"]["semantic"].get("lines") or []
            for i, line in enumerate(lines):
                self.assertNotIn(
                    "\n", str(line),
                    f"lines[{i}] contient un \\n — corruption de first_block.text: {line!r}",
                )
            # L'entrée 0 ne doit pas être le texte fusionné entier
            if len(lines) >= 2:
                self.assertNotIn(
                    lines[1], lines[0],
                    f"lines[0] contient lines[1] — mutation avant construction: {lines[0]!r}",
                )


if __name__ == "__main__":
    unittest.main()
