from __future__ import annotations

from pathlib import Path

from purh_editorial.latex.semantic_model import (
    BibliographyBlock,
    Bold,
    Book,
    DivisionKind,
    FootnoteRef,
    InlineNode,
    Italic,
    ListBlock,
    Paragraph,
    QuoteBlock,
    SmallCaps,
    Subscript,
    Superscript,
    TextRun,
    VerseBlock,
)


class LatexRenderer:
    def render_book(self, book: Book) -> str:
        lines = [
            r"\documentclass[11pt,oneside,openany]{memoir}",
            r"\usepackage{fontspec}",
            r"\usepackage{polyglossia}",
            r"\setmainlanguage{french}",
            r"\usepackage{csquotes}",
            r"\usepackage{hyperref}",
            r"\begin{document}",
            rf"\title{{{self._escape(book.metadata.title)}}}",
        ]
        if book.metadata.contributors:
            lines.append(rf"\author{{{self._escape(' ; '.join(book.metadata.contributors))}}}")
        lines.extend([r"\maketitle", ""])

        for division in book.divisions:
            chapter_command = r"\chapter" if division.kind == DivisionKind.CHAPTER else r"\chapter*"
            lines.append(rf"{chapter_command}{{{self._escape(division.title)}}}")
            if division.kind != DivisionKind.CHAPTER:
                lines.append(rf"\addcontentsline{{toc}}{{chapter}}{{{self._escape(division.title)}}}")
            for block in division.blocks:
                rendered = self._render_block(block)
                if rendered:
                    lines.append(rendered)
                    lines.append("")

        lines.append(r"\end{document}")
        return "\n".join(lines) + "\n"

    def write_book(self, book: Book, output_tex: Path) -> Path:
        output_tex.parent.mkdir(parents=True, exist_ok=True)
        output_tex.write_text(self.render_book(book), encoding="utf-8")
        return output_tex

    def _render_paragraph(self, paragraph: Paragraph) -> str:
        return self._render_inline_nodes(paragraph.content)

    def _render_block(self, block) -> str:
        if isinstance(block, Paragraph):
            return self._render_paragraph(block)
        if isinstance(block, QuoteBlock):
            paragraphs: list[str] = []
            for paragraph in block.paragraphs:
                rendered = self._render_paragraph(paragraph)
                if rendered:
                    paragraphs.append(rendered)
            if not paragraphs:
                return ""
            return "\n".join([r"\begin{quote}", *paragraphs, r"\end{quote}"])
        if isinstance(block, VerseBlock):
            lines = [self._render_inline_nodes(line.content) + r"\\" for line in block.lines]
            return "\n".join([r"\begin{verse}", *lines, r"\end{verse}"])
        if isinstance(block, ListBlock):
            env = "enumerate" if block.ordered else "itemize"
            entries = [rf"\item {self._render_inline_nodes(item.content)}" for item in block.items]
            return "\n".join([rf"\begin{{{env}}}", *entries, rf"\end{{{env}}}"])
        if isinstance(block, BibliographyBlock):
            lines = [r"\section*{Bibliographie}", r"\addcontentsline{toc}{section}{Bibliographie}"]
            for item in block.items:
                lines.append(rf"\noindent {self._render_inline_nodes(item.content)}\par")
            return "\n".join(lines)
        return ""

    def _render_inline_nodes(self, nodes: list[InlineNode]) -> str:
        return "".join(self._render_inline_node(node) for node in nodes)

    def _render_inline_node(self, node: InlineNode) -> str:
        if isinstance(node, TextRun):
            return self._escape(node.text)
        if isinstance(node, Italic):
            return rf"\textit{{{self._render_inline_nodes(node.children)}}}"
        if isinstance(node, Bold):
            return rf"\textbf{{{self._render_inline_nodes(node.children)}}}"
        if isinstance(node, SmallCaps):
            return rf"\textsc{{{self._render_inline_nodes(node.children)}}}"
        if isinstance(node, Superscript):
            return rf"\textsuperscript{{{self._render_inline_nodes(node.children)}}}"
        if isinstance(node, Subscript):
            return rf"$_{{{self._render_inline_nodes(node.children)}}}$"
        if isinstance(node, FootnoteRef):
            return rf"\footnote{{{self._render_inline_nodes(node.content)}}}"
        return ""

    def _escape(self, value: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "{": r"\{",
            "}": r"\}",
            "$": r"\$",
            "&": r"\&",
            "%": r"\%",
            "#": r"\#",
            "_": r"\_",
            "^": r"\textasciicircum{}",
            "~": r"\textasciitilde{}",
        }
        return "".join(replacements.get(ch, ch) for ch in value)
