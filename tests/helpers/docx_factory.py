from __future__ import annotations

import base64
import zipfile
from pathlib import Path

from docx import Document as DocxDoc

# PNG 1x1 transparent, utilisé pour tous les tests d'images synthétiques.
PNG_1X1_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
# JPEG 1x1 blanc minimal.
JPEG_1X1_BYTES = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
)


def create_minimal_template_docx(path: Path) -> Path:
    """Gabarit DOCX minimal et public, pour les tests qui n'ont pas besoin du vrai
    gabarit Métopes (privé, non suivi dans ce dépôt — voir docs/CORPUS_ET_FIXTURES.md)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    DocxDoc().save(path)
    return path


DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Texte  </w:t></w:r>
      <w:r><w:rPr><w:i/></w:rPr><w:t>italique</w:t></w:r>
      <w:r><w:rPr><w:b/></w:rPr><w:t> gras</w:t></w:r>
      <w:r><w:rPr><w:smallCaps/></w:rPr><w:t> sc</w:t></w:r>
      <w:r><w:rPr><w:vertAlign w:val="subscript"/></w:rPr><w:t> sub</w:t></w:r>
      <w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t> sup</w:t></w:r>
      <w:r><w:footnoteReference w:id="2"/></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""

FOOTNOTES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:t>separator</w:t></w:r></w:p></w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:t>continuation</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="2">
    <w:p>
      <w:r><w:footnoteRef/></w:r>
      <w:r><w:t>Note </w:t></w:r>
      <w:r><w:rPr><w:i/></w:rPr><w:t>italique</w:t></w:r>
      <w:r><w:rPr><w:b/></w:rPr><w:t> gras</w:t></w:r>
      <w:r><w:rPr><w:smallCaps/></w:rPr><w:t> sc</w:t></w:r>
      <w:r><w:rPr><w:vertAlign w:val="subscript"/></w:rPr><w:t> sub</w:t></w:r>
      <w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t> sup</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>
"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
</w:styles>
"""

CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Fixture inline</dc:title>
  <dc:creator>Testeur</dc:creator>
  <dc:language>fr</dc:language>
</cp:coreProperties>
"""


def create_rich_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", DOC_XML)
        archive.writestr("word/footnotes.xml", FOOTNOTES_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


HYPERLINK_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Voir </w:t></w:r>
      <w:hyperlink r:id="rId1">
        <w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr><w:t>le site des PURH</w:t></w:r>
      </w:hyperlink>
      <w:r><w:t> pour plus de details.</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""

HYPERLINK_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://purh.univ-rouen.fr/" TargetMode="External"/>
</Relationships>
"""


def create_hyperlink_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", HYPERLINK_DOC_XML)
        archive.writestr("word/_rels/document.xml.rels", HYPERLINK_RELS_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


# w:id="0" est ici reutilise par une vraie note de contenu (numerotation Word qui ne
# reserve pas systematiquement -1/0 aux marqueurs separator/continuationSeparator).
ZERO_ID_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Appel de note</w:t></w:r>
      <w:r><w:footnoteReference w:id="0"/></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""

ZERO_ID_FOOTNOTES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:t>separator</w:t></w:r></w:p></w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="1"><w:p><w:r><w:t>continuation</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="0">
    <w:p>
      <w:r><w:footnoteRef/></w:r>
      <w:r><w:t> Note reelle numerotee zero.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>
"""


def create_docx_with_zero_id_footnote(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", ZERO_ID_DOC_XML)
        archive.writestr("word/footnotes.xml", ZERO_ID_FOOTNOTES_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


TABLE_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Avant tableau</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="0" w:type="auto"/>
      </w:tblPr>
      <w:tblGrid>
        <w:gridCol w:w="4000"/>
        <w:gridCol w:w="4000"/>
      </w:tblGrid>
      <w:tr>
        <w:tc>
          <w:p><w:r><w:t>VIII,Pr.,</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:p><w:r><w:t>VIII;Pr.,18</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Après tableau</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""


def create_table_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", TABLE_DOC_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


BLANK_SEPARATED_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Prose avant le bloc.</w:t></w:r></w:p>
    <w:p/>
    <w:p><w:r><w:t>C'est moi qui si longtemps le plaisir de vos yeux,</w:t></w:r></w:p>
    <w:p><w:r><w:t>Vous ai fait de ce nom remercier les Dieux,</w:t></w:r></w:p>
    <w:p><w:r><w:t>Et pour qui tant de fois prodiguant vos caresses,</w:t></w:r></w:p>
    <w:p><w:r><w:t>Vous n'avez point du sang dedaigne les faiblesses.</w:t></w:r></w:p>
    <w:p/>
    <w:p><w:r><w:t>La prose reprend après le bloc.</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""


def create_blank_separated_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", BLANK_SEPARATED_DOC_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


MINIMAL_BLANK_BOUNDARY_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Paragraphe A</w:t></w:r></w:p>
    <w:p/>
    <w:p><w:r><w:t>Paragraphe B</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""


POETRY_CANDIDATE_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Je vois </w:t></w:r>
      <w:r><w:rPr><w:i/></w:rPr><w:t>Phèdre</w:t></w:r>
      <w:r><w:t> venir.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Deuxième vers</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""


def create_minimal_blank_boundary_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", MINIMAL_BLANK_BOUNDARY_DOC_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


def create_poetry_candidate_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", POETRY_CANDIDATE_DOC_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


# DOCX avec un paragraphe de style "Titre" (sans numéro de niveau) : l'importeur
# le reconnaît comme Heading mais ne peut pas extraire heading_level → le pivot
# validator lève une erreur → export TEI bloqué.
TITRE_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Titre">
    <w:name w:val="Titre"/>
  </w:style>
</w:styles>
"""

TITRE_DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Paragraphe introductif.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Titre"/></w:pPr>
      <w:r><w:t>Un motif dramaturgique récurrent</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""


def create_titre_docx(path: Path) -> Path:
    """DOCX dont un heading de style 'Titre' (sans numéro) déclenche l'erreur pivot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", TITRE_DOC_XML)
        archive.writestr("word/styles.xml", TITRE_STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
    return path


# ── Images DOCX synthétiques (Partie D13) ────────────────────────────────────

_IMG_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:v="urn:schemas-microsoft-com:vml" '
    'xmlns:o="urn:schemas-microsoft-com:office:office"'
)


def _inline_picture_xml(*, rid_attr: str, cx: int = 914400, cy: int = 914400,
                         docpr_id: int = 1, name: str = "Picture", descr: str = "",
                         title: str = "", anchor: bool = False) -> str:
    extra = ""
    if descr:
        extra += f' descr="{descr}"'
    if title:
        extra += f' title="{title}"'
    tag = "wp:anchor" if anchor else "wp:inline"
    anchor_extra_attrs = (
        ' distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="1" '
        'behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1"'
        if anchor else ""
    )
    anchor_extra_children = (
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>'
        if anchor else ""
    )
    return (
        f'<w:r><w:drawing><{tag}{anchor_extra_attrs}>'
        f'{anchor_extra_children}'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{docpr_id}" name="{name}"{extra}/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic><pic:blipFill><a:blip {rid_attr}/></pic:blipFill></pic:pic>'
        f'</a:graphicData></a:graphic></{tag}></w:drawing></w:r>'
    )


IMAGES_DOC_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document {_IMG_NS}>
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Avant image.</w:t></w:r>
      {_inline_picture_xml(rid_attr='r:embed="rId1"', docpr_id=1, name="Picture 1", descr="Texte alternatif", title="Titre image")}
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="TEI_figure_caption"/></w:pPr>
      <w:r><w:t>Légende de la première image.</w:t></w:r>
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      {_inline_picture_xml(rid_attr='r:embed="rId2"', cx=500000, cy=500000, docpr_id=2, name="Picture 2", anchor=True)}
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      {_inline_picture_xml(rid_attr='r:embed="rId3"', cx=300000, cy=300000, docpr_id=3, name="Picture 3 JPEG")}
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      {_inline_picture_xml(rid_attr='r:embed="rId4"', docpr_id=4, name="Picture 4 reused bytes")}
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      {_inline_picture_xml(rid_attr='r:link="rId5"', cx=200000, cy=200000, docpr_id=5, name="Picture 5 external")}
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:drawing><wp:inline>
        <wp:extent cx="400000" cy="400000"/>
        <wp:docPr id="6" name="Chart 1"/>
        <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">
          <c:chart r:id="rId6"/>
        </a:graphicData></a:graphic>
      </wp:inline></w:drawing></w:r>
    </w:p>
    <w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>
      <w:r><w:t>Appel de note avec image</w:t></w:r>
      <w:r><w:footnoteReference w:id="2"/></w:r>
    </w:p>
    <w:tbl>
      <w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr>
      <w:tblGrid><w:gridCol w:w="4000"/></w:tblGrid>
      <w:tr><w:tc><w:p>
        {_inline_picture_xml(rid_attr='r:embed="rId7"', cx=300000, cy=300000, docpr_id=7, name="Picture in table")}
      </w:p></w:tc></w:tr>
    </w:tbl>
    <w:sectPr/>
  </w:body>
</w:document>
"""

IMAGES_FOOTNOTES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes {_IMG_NS}>
  <w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:t>separator</w:t></w:r></w:p></w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:t>continuation</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="2">
    <w:p>
      <w:r><w:footnoteRef/></w:r>
      <w:r><w:t> Voir figure : </w:t></w:r>
      {_inline_picture_xml(rid_attr='r:embed="rId1"', cx=300000, cy=300000, docpr_id=8, name="Picture in note")}
    </w:p>
  </w:footnote>
</w:footnotes>
"""

IMAGES_DOCUMENT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image3.jpg"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image4.png"/>
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="https://example.org/external.png" TargetMode="External"/>
  <Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image_table.png"/>
</Relationships>
"""

IMAGES_FOOTNOTES_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image_note.png"/>
</Relationships>
"""


def create_images_docx(path: Path) -> Path:
    """DOCX synthétique couvrant : inline PNG (alt+titre+légende), ancrée, JPEG,
    réutilisation d'octets identiques (dédup sha256), lien externe, graphique
    (objet complexe), image dans une note, image dans un tableau."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", IMAGES_DOC_XML)
        archive.writestr("word/footnotes.xml", IMAGES_FOOTNOTES_XML)
        archive.writestr("word/_rels/document.xml.rels", IMAGES_DOCUMENT_RELS_XML)
        archive.writestr("word/_rels/footnotes.xml.rels", IMAGES_FOOTNOTES_RELS_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("docProps/core.xml", CORE_XML)
        archive.writestr("word/media/image1.png", PNG_1X1_BYTES)
        archive.writestr("word/media/image2.png", PNG_1X1_BYTES)
        archive.writestr("word/media/image3.jpg", JPEG_1X1_BYTES)
        archive.writestr("word/media/image4.png", PNG_1X1_BYTES)
        archive.writestr("word/media/image_table.png", PNG_1X1_BYTES)
        archive.writestr("word/media/image_note.png", PNG_1X1_BYTES)
    return path
