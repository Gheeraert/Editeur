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
        title_escaped = self._escape(book.metadata.title)
        contributors = book.metadata.contributors
        author_escaped = self._escape(" ; ".join(contributors)) if contributors else ""

        lines = [
            r"\documentclass[12pt,twoside,final,openright]{book}",
            r"\usepackage{fontspec}",
            r"\usepackage{microtype}",
            r"\usepackage{ulem}",
            r"\normalem",
            r"",
            r"\usepackage{csquotes}",
            r'\MakeOuterQuote{"}',
            r"\makeatletter",
            r"\renewenvironment*{displayquote}",
            r"  {\begingroup\setlength{\leftmargini}{1cm}\csq@getcargs{\csq@bdquote{}{}}}",
            r"  {\csq@edquote\endgroup}",
            r"\makeatother",
            r"\renewcommand{\mkbegdispquote}",
            r"  {\fontsize{12pt}{11pt}\selectfont\textooquote}",
            r"",
            r"\usepackage{polyglossia}",
            r"\setmainlanguage{french}",
            r"",
            r"\usepackage{enumitem}",
            r"\setlist[itemize]{topsep=0pt, itemsep=2pt, parsep=0pt}",
            r"",
            r"\usepackage{hyperref}",
            r"\hypersetup{hidelinks}",
            r"",
            r"\setmainfont{Chaparral Pro}",
            r"",
            r"\newfontfamily\JosefinSans{Josefin Sans}[",
            r"  UprightFont = * Bold,",
            r"  ItalicFont  = * Italic",
            r"]",
            r"",
            r"\usepackage{anyfontsize}",
            r"",
            r"\usepackage{titlesec}",
            r"\titleformat{\chapter}{\JosefinSans\LARGE\bfseries}{\thechapter}{1em}{}",
            r"\titleformat{\section}{\JosefinSans\Large\bfseries}{\thesection}{1em}{}",
            r"\titlespacing*{\section}{0pt}{10pt}{5pt}",
            r"\titleformat{\subsection}{\JosefinSans\large\bfseries}{\thesubsection}{1em}{}",
            r"\titlespacing*{\subsection}{0pt}{10pt}{5pt}",
            r"\titleformat{\subsubsection}{\JosefinSans\normalsize\bfseries}{\thesubsection}{1em}{}",
            r"\titlespacing*{\subsubsection}{0pt}{10pt}{3pt}",
            r"",
            r"\usepackage[paperwidth=152mm, paperheight=229mm, top=25mm, bottom=25mm, inner=20mm, outer=20mm]{geometry}",
            r"",
            r"\usepackage{fancyhdr}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            rf"\fancyhead[LE]{{\textit{{{title_escaped}}}}}",
            r"\fancyhead[RO]{\textit{\leftmark}}",
            r"\fancyfoot[LE,RO]{\thepage}",
            r"\renewcommand{\headrulewidth}{0.4pt}",
            r"\renewcommand{\footrulewidth}{0pt}",
            r"\fancypagestyle{plain}{",
            r"    \fancyhf{}",
            r"    \fancyfoot[LE,RO]{\thepage}",
            r"    \renewcommand{\headrulewidth}{0pt}",
            r"}",
            r"",
            r"\usepackage{emptypage}",
            r"\usepackage{afterpage}",
            r"",
            r"\usepackage[",
            r"  backend=biber,",
            r"  style=ext-verbose-inote,",
            r"  citereset=chapter,",
            r"  autopunct=false",
            r"]{biblatex}",
            r"% \addbibresource{bibliography.bib}",
            r"",
            r"\usepackage{perpage}",
            r"\MakePerPage{footnote}",
            r"",
            r"\usepackage{verse}",
            r"\usepackage{longtable}",
            r"\usepackage{array}",
            r"\newcommand{\purhTableSize}{\small}",
            r"",
            r"\renewcommand{\baselinestretch}{1}",
            r"\setlength{\parindent}{5mm}",
            r"\setlength{\parskip}{4pt}",
            r"",
            r"\setlength{\footnotesep}{2mm}",
            r"\usepackage[marginal]{footmisc}",
            r"",
            r"\pretolerance=100",
            r"\tolerance=500",
            r"\hyphenpenalty=500",
            r"\exhyphenpenalty=500",
            r"\emergencystretch=3em",
            r"\clubpenalty=10000",
            r"\widowpenalty=10000",
            r"\displaywidowpenalty=10000",
            r"",
            r"\renewcommand{\labelitemi}{--}",
            r"",
            r"\usepackage{setspace}",
            r"\usepackage{graphicx}",
            r"\usepackage[center, cam, cross]{crop}",
            r"",
            rf"\title{{{title_escaped}}}",
        ]

        if contributors:
            lines.append(rf"\author{{{author_escaped}}}")

        lines.extend([
            r"\begin{document}",
            r"\fontsize{13pt}{15pt}\selectfont",
            r"",
            r"\newpage",
            r"\thispagestyle{empty}",
            r"\vspace*{1cm}",
            r"\begin{center}",
            r"    \onehalfspacing",
            rf"    {{\LARGE\textsc{{{title_escaped}}}}}",
            r"\end{center}",
            r"\newpage",
            r"",
            r"\begin{titlepage}",
            r"    \centering",
            r"    \vspace*{3cm}",
            rf"    {{\huge\bfseries {title_escaped} \par}}",
            r"    \vspace{2cm}",
        ])

        if contributors:
            lines.append(rf"    {{\Large {author_escaped}\par}}")

        lines.extend([
            r"    \vfill",
            r"    {\Large Presses Universitaires de Rouen et du Havre \par}",
            r"    \vspace{0.5cm}",
            r"    {\large 2025}",
            r"\end{titlepage}",
            r"",
        ])

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

        lines.extend([r"% \printbibliography", r"\end{document}"])
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
            return "\n".join([r"\begin{displayquote}", *paragraphs, r"\end{displayquote}"])
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
