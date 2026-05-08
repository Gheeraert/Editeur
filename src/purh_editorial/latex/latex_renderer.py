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
    TableBlock,
    TableCell,
    TextRun,
    VerseBlock,
)


class LatexRenderer:
    def render_book(self, book: Book) -> str:
        meta = book.metadata
        lines = [
            r"\documentclass[11pt,oneside,openany]{memoir}",
            r"\usepackage{fontspec}",
            r"\usepackage{polyglossia}",
            r"\setmainlanguage{french}",
            r"\setmainfont{TeX Gyre Pagella}",
            r"\setsansfont[Scale=MatchLowercase]{TeX Gyre Heros}",
            r"\setmonofont{Latin Modern Mono}",
            r"\usepackage[final]{microtype}",
            r"\usepackage{csquotes}",
            r"\usepackage{hyperref}",
            r"\usepackage{verse}",
            r"\usepackage{longtable}",
            r"\usepackage{array}",
            r"\usepackage{xcolor}",
            r"\setstocksize{230mm}{155mm}",
            r"\settrimmedsize{\stockheight}{\stockwidth}{*}",
            r"\setlrmarginsandblock{23mm}{22mm}{*}",
            r"\setulmarginsandblock{24mm}{22mm}{*}",
            r"\checkandfixthelayout",
            r"\setlength{\parindent}{1.25em}",
            r"\setlength{\parskip}{0pt}",
            r"\renewcommand{\footnotesize}{\small}",
            r"\newcommand{\purhTableSize}{\small}",
            r"\pagestyle{plain}",
            r"\begin{document}",
        ]
        lines.extend(self._render_title_pages(meta))
        lines.append("")

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

    def _render_title_pages(self, meta) -> list[str]:
        """Génère les pages liminaires : faux-titre, titre complet, colophon."""
        lines: list[str] = []
        e = self._escape

        has_any = bool(meta.title)
        if not has_any:
            return lines

        # ── Faux-titre ────────────────────────────────────────────────────────
        lines += [
            r"\begin{titlingpage}",
            r"\thispagestyle{empty}",
            r"\vspace*{\fill}",
            r"\begin{center}",
            rf"{{\sffamily\large {e(meta.title)}}}",
            r"\end{center}",
            r"\vspace*{\fill}",
            r"\end{titlingpage}",
            r"\cleardoublepage",
            "",
        ]

        # ── Page de titre complète ─────────────────────────────────────────────
        lines += [r"\begin{titlingpage}", r"\thispagestyle{empty}"]

        # Série / collection (en haut, gris clair)
        series_parts: list[str] = []
        if meta.series_title:
            series_parts.append(e(meta.series_title))
        if meta.collection:
            series_parts.append(e(meta.collection))
        if meta.volume_number:
            series_parts.append(f"vol.~{e(meta.volume_number)}")
        if series_parts:
            lines += [
                r"\vspace*{18mm}",
                r"\begin{center}",
                rf"{{\sffamily\small\color{{gray}} {' — '.join(series_parts)}}}",
                r"\end{center}",
            ]
        else:
            lines.append(r"\vspace*{26mm}")

        # Titre & sous-titre
        lines += [
            r"\vspace*{\fill}",
            r"\begin{center}",
            rf"{{\sffamily\LARGE\bfseries {e(meta.title)}}}",
        ]
        if meta.subtitle:
            lines += [
                r"\par\medskip",
                rf"{{\sffamily\large\itshape {e(meta.subtitle)}}}",
            ]
        lines.append(r"\end{center}")

        # Auteur(s)
        if meta.contributors:
            names = " \\and ".join(e(n) for n in meta.contributors)
            lines += [
                r"\vspace{8mm}",
                r"\begin{center}",
                rf"{{\sffamily\normalsize {names}}}",
                r"\end{center}",
            ]

        # Direction scientifique
        if meta.scientific_editors:
            label = "Sous la direction de" if len(meta.scientific_editors) > 1 else "Sous la direction de"
            names = ", ".join(e(n) for n in meta.scientific_editors)
            lines += [
                r"\vspace{4mm}",
                r"\begin{center}",
                rf"{{\sffamily\small {e(label)}\\[2pt] {names}}}",
                r"\end{center}",
            ]

        # Traducteur(s)
        if meta.translators:
            label = "Traduit par"
            names = ", ".join(e(n) for n in meta.translators)
            lines += [
                r"\vspace{4mm}",
                r"\begin{center}",
                rf"{{\sffamily\small {e(label)}\\[2pt] {names}}}",
                r"\end{center}",
            ]

        # Éditeur & lieu en bas de page
        lines.append(r"\vspace*{\fill}")
        pub = meta.publisher or "Presses universitaires de Rouen et du Havre"
        place = meta.pub_place or "Mont-Saint-Aignan"
        date_str = meta.publication_date or ""
        pub_line = f"{e(pub)} — {e(place)}"
        if date_str:
            pub_line += f" — {e(date_str)}"
        lines += [
            r"\begin{center}",
            rf"\rule{{0.5\textwidth}}{{0.4pt}}\\[4pt]",
            rf"{{\sffamily\footnotesize {pub_line}}}",
            r"\end{center}",
            r"\end{titlingpage}",
            r"\cleardoublepage",
            "",
        ]

        # ── Colophon (verso page de titre) ────────────────────────────────────
        lines += [
            r"\thispagestyle{empty}",
            r"\vspace*{\fill}",
            r"\begin{flushleft}",
            rf"{{\sffamily\footnotesize",
        ]

        # Responsabilité éditoriale
        if meta.contributors:
            lines.append(rf"\textbf{{{e(meta.title)}}} / {', '.join(e(n) for n in meta.contributors)}\\[4pt]")
        else:
            lines.append(rf"\textbf{{{e(meta.title)}}}\\[4pt]")

        if meta.edition_note:
            lines.append(rf"{e(meta.edition_note)}\\[4pt]")

        # Éditeur
        lines += [
            rf"{{\copyright}}~{e(date_str[:4] if date_str else '')} {e(pub)}, {e(place)}\\[4pt]",
        ]

        # ISBN / ISSN
        if meta.isbn_print:
            lines.append(rf"ISBN (imprimé) : {e(meta.isbn_print)}\\")
        if meta.isbn_epub:
            lines.append(rf"ISBN (ePub) : {e(meta.isbn_epub)}\\")
        if meta.isbn_pdf:
            lines.append(rf"ISBN (PDF) : {e(meta.isbn_pdf)}\\")
        if meta.issn:
            lines.append(rf"ISSN : {e(meta.issn)}\\")

        # Dépôt légal
        if meta.legal_deposit_date:
            lines.append(rf"Dépôt légal : {e(meta.legal_deposit_date)}\\")
        elif date_str:
            lines.append(rf"Dépôt légal : {e(date_str)}\\")

        lines += [
            r"}}",
            r"\end{flushleft}",
            r"\clearpage",
            "",
        ]
        return lines

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
            return "\n".join([r"\begin{quote}\small", *paragraphs, r"\end{quote}"])
        if isinstance(block, VerseBlock):
            rendered_lines = []
            for line in block.lines:
                content = self._render_inline_nodes(line.content)
                # After \\ or \begin{verse}, a leading [ is parsed as an optional
                # argument (spacing or width). An empty group {} neutralises it.
                if content.startswith("["):
                    content = "{}" + content
                rendered_lines.append(content + r"\\")
            return "\n".join([r"\begin{verse}", *rendered_lines, r"\end{verse}"])
        if isinstance(block, ListBlock):
            env = "enumerate" if block.ordered else "itemize"
            entries = [rf"\item {self._render_inline_nodes(item.content)}" for item in block.items]
            return "\n".join([rf"\begin{{{env}}}", *entries, rf"\end{{{env}}}"])
        if isinstance(block, BibliographyBlock):
            lines = [r"\section*{Bibliographie}", r"\addcontentsline{toc}{section}{Bibliographie}"]
            for item in block.items:
                lines.append(rf"\noindent {self._render_inline_nodes(item.content)}\par")
            return "\n".join(lines)
        if isinstance(block, TableBlock):
            return self._render_table_block(block)
        return ""

    def _render_table_block(self, table: TableBlock) -> str:
        if table.export_comment:
            return f"% {table.export_comment}"

        row_count = len(table.rows)
        col_count = max((len(row.cells) for row in table.rows), default=0)
        if row_count == 0 or col_count == 0:
            return "% table_export_fallback empty_table"

        if col_count > 8:
            return f"% table_export_fallback too_many_columns rows={row_count} cols={col_count}"

        col_width = 0.92 / col_count
        col_spec = " ".join([rf"p{{{col_width:.2f}\textwidth}}"] * col_count)
        lines = [
            f"% table_exported_to_latex rows={row_count} cols={col_count}",
            r"\begingroup",
            r"\purhTableSize",
            rf"\begin{{longtable}}{{{col_spec}}}",
        ]
        for row in table.rows:
            rendered_cells: list[str] = []
            for cell in row.cells:
                rendered_cells.append(self._render_table_cell(cell))
            if len(rendered_cells) < col_count:
                rendered_cells.extend([""] * (col_count - len(rendered_cells)))
            lines.append(" & ".join(rendered_cells) + r" \\")
        lines.append(r"\end{longtable}")
        lines.append(r"\endgroup")
        return "\n".join(lines)

    def _render_table_cell(self, cell: TableCell) -> str:
        parts: list[str] = []
        for paragraph in cell.paragraphs:
            rendered = self._render_paragraph(paragraph).strip()
            if rendered:
                parts.append(rendered)
        return r" \par ".join(parts)

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
