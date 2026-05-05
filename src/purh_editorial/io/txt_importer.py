from __future__ import annotations

from pathlib import Path

from purh_editorial.io.importer_base import DocumentImporter
from purh_editorial.model import Document, Heading, Metadata, Paragraph
from purh_editorial.utils import make_id


class TxtImporter(DocumentImporter):
    supported_extensions = (".txt", ".md")

    def load(self, path: Path) -> Document:
        text = self._read_text(path)
        blocks = []
        buffer: list[str] = []
        block_index = 1

        def flush_paragraph() -> None:
            nonlocal block_index
            if not buffer:
                return
            paragraph_text = " ".join(line.strip() for line in buffer if line.strip())
            if paragraph_text:
                blocks.append(Paragraph(block_id=f"p{block_index}", text=paragraph_text))
                block_index += 1
            buffer.clear()

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\n")
            if not line.strip():
                flush_paragraph()
                continue

            if line.startswith("#"):
                flush_paragraph()
                level = min(len(line) - len(line.lstrip("#")), 6)
                heading_text = line.lstrip("#").strip()
                blocks.append(Heading(block_id=f"h{block_index}", text=heading_text,
                                      attributes={"heading_level": max(level, 1)}))
                block_index += 1
                continue

            if self._looks_like_heading(line):
                flush_paragraph()
                blocks.append(Heading(block_id=f"h{block_index}", text=line.strip(),
                                      attributes={"heading_level": 1}))
                block_index += 1
                continue

            buffer.append(line)

        flush_paragraph()

        metadata = Metadata(
            title=blocks[0].text if blocks and blocks[0].block_type == "heading" else path.stem,
            source_label=path.name,
        )
        return Document(
            document_id=make_id("doc"),
            source_path=str(path),
            source_format="txt",
            metadata=metadata,
            blocks=blocks,
            original_text=text,
        )

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            return False
        has_sentence_punct = any(char in stripped for char in ".!?;:")
        mostly_upper = stripped.upper() == stripped and any(ch.isalpha() for ch in stripped)
        return mostly_upper and not has_sentence_punct

    @staticmethod
    def _read_text(path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="replace")
