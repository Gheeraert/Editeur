from __future__ import annotations

from pathlib import Path

from purh_editorial.latex.semantic_model import (
    Bold,
    Book,
    FootnoteRef,
    InlineNode,
    Italic,
    Paragraph,
    SmallCaps,
    Subscript,
    Superscript,
    TextRun,
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
            lines.append(rf"\chapter*{{{self._escape(division.title)}}}")
            lines.append(rf"\addcontentsline{{toc}}{{chapter}}{{{self._escape(division.title)}}}")
            for paragraph in division.paragraphs:
                rendered = self._render_paragraph(paragraph)
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
