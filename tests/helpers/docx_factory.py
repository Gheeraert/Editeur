from __future__ import annotations

import zipfile
from pathlib import Path


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
  <w:footnote w:id="-1"><w:p><w:r><w:t>separator</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="0"><w:p><w:r><w:t>continuation</w:t></w:r></w:p></w:footnote>
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
