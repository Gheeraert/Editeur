from __future__ import annotations

"""Rendu LaTeX à partir du modèle sémantique minimal.

Ce module convertit les objets définis dans ``semantic_model.py`` en une
chaîne LaTeX complète, prête à être compilée avec LuaLaTeX.

Choix de conception pour la V1
------------------------------
- rester lisible et pédagogique ;
- produire un PDF éditeur sobre et robuste ;
- éviter les raffinements typographiques prématurés ;
- couvrir correctement les cas PURH les plus fréquents.

Le renderer assume que le parseur TEI a déjà produit un modèle propre :
- notes séparées du flux ;
- inline structurés ;
- divisions hiérarchisées ;
- figures et bibliographie déjà identifiées.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .semantic_model import (
    BibliographyBlock,
    BibliographyItem,
    BlockNode,
    Book,
    Bold,
    Division,
    DivisionType,
    FigureBlock,
    Footnote,
    InlineNode,
    InlineQuote,
    Italic,
    Link,
    ListBlock,
    ListItem,
    ListKind,
    NoteRef,
    Paragraph,
    QuoteBlock,
    Section,
    SmallCaps,
    Subscript,
    Superscript,
    TextRun,
    TitlePageBlock,
    VerseBlock,
    VerseLine,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LatexRenderOptions:
    """Options simples de rendu pour la V1."""

    document_class: str = "memoir"
    font_size_pt: int = 11
    paper_width_mm: int = 155
    paper_height_mm: int = 230

    # Marges / bloc de texte : valeurs prudentes et faciles à ajuster ensuite.
    inner_margin_mm: int = 23
    outer_margin_mm: int = 22
    upper_margin_mm: int = 24
    lower_margin_mm: int = 22

    main_font: str = "TeX Gyre Pagella"
    sans_font: str = "TeX Gyre Heros"
    mono_font: str = "Latin Modern Mono"
    main_language: str = "french"

    include_toc: bool = True
    hyperlink_color: str = "black"
    oneside: bool = True
    openany: bool = True

    figure_max_width: str = r"0.95\linewidth"
    quote_left_margin_em: float = 2.0
    bibliography_hangindent_em: float = 1.5

    show_toc_in_pdf_bookmarks: bool = True


# ---------------------------------------------------------------------------
# Renderer principal
# ---------------------------------------------------------------------------


class LatexRenderer:
    """Convertit un ``Book`` en document LaTeX complet."""

    def __init__(self, options: LatexRenderOptions | None = None) -> None:
        self.options = options or LatexRenderOptions()
        self._current_notes: dict[str, Footnote] = {}
        self._in_footnote = False
        self._appendix_started = False

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def render_book(self, book: Book) -> str:
        """Retourne le document LaTeX complet pour le livre donné."""

        parts: list[str] = [self._render_preamble(book), "\\begin{document}"]

        parts.append(self._render_volume_title_page(book))

        parts.append("\\frontmatter")
        parts.append(self._render_front_divisions(book))

        if self.options.include_toc:
            parts.append("\\cleardoublepage")
            parts.append("\\tableofcontents")

        parts.append("\\mainmatter")
        parts.append(self._render_body_divisions(book))

        if book.back_divisions:
            parts.append("\\backmatter")
            parts.append(self._render_back_divisions(book))

        parts.append("\\end{document}")
        return "\n\n".join(part for part in parts if part.strip()) + "\n"

    def write_book(self, book: Book, output_path: str | Path) -> Path:
        """Écrit le document LaTeX sur disque et retourne le chemin."""

        output = Path(output_path)
        output.write_text(self.render_book(book), encoding="utf-8")
        return output


# ---------------------------------------------------------------------------
# Preambule
# ---------------------------------------------------------------------------

    def _render_preamble(self, book: Book) -> str:
        class_options = [f"{self.options.font_size_pt}pt"]
        if self.options.oneside:
            class_options.append("oneside")
        if self.options.openany:
            class_options.append("openany")
        class_options_str = ",".join(class_options)

        title = self._escape_text(book.metadata.title)
        author = self._escape_text(self._join_contributor_names(book.metadata.contributors))

        return rf"""
\documentclass[{class_options_str}]{{{self.options.document_class}}}

\usepackage{{fontspec}}
\usepackage{{polyglossia}}
\setmainlanguage{{{self.options.main_language}}}
\setmainfont{{{self.options.main_font}}}
\setsansfont{{{self.options.sans_font}}}
\setmonofont{{{self.options.mono_font}}}

\usepackage[final]{{microtype}}
\usepackage{{graphicx}}
\usepackage{{csquotes}}
\usepackage{{hyperref}}
\usepackage{{bookmark}}
\usepackage{{caption}}
\usepackage{{enumitem}}
\usepackage{{verse}}
\usepackage{{ragged2e}}
\usepackage{{xurl}}

\hypersetup{{
  unicode=true,
  pdftitle={{{title}}},
  pdfauthor={{{author}}},
  colorlinks=true,
  allcolors={self.options.hyperlink_color}
}}

% -----------------------------------------------------------------
% Format de page PURH V1 (sobre et ajustable)
% -----------------------------------------------------------------
\setstocksize{{{self.options.paper_height_mm}mm}}{{{self.options.paper_width_mm}mm}}
\settrimmedsize{{\stockheight}}{{\stockwidth}}{{*}}
\setlrmarginsandblock{{{self.options.inner_margin_mm}mm}}{{{self.options.outer_margin_mm}mm}}{{*}}
\setulmarginsandblock{{{self.options.upper_margin_mm}mm}}{{{self.options.lower_margin_mm}mm}}{{*}}
\checkandfixthelayout

% -----------------------------------------------------------------
% Réglages de base
% -----------------------------------------------------------------
\setsecnumdepth{{subsection}}
\settocdepth{{subsection}}
\captionnamefont{{\small\bfseries}}
\captiontitlefont{{\small}}
\footnotesize
\AtBeginDocument{{\normalsize}}
\setlength{{\parindent}}{{1.25em}}
\setlength{{\parskip}}{{0pt}}
\setlength{{\footmarkwidth}}{{1.8em}}
\setlength{{\footmarksep}}{{0.4em}}
\setlength{{\skip\footins}}{{1.1\baselineskip}}

% -----------------------------------------------------------------
% Macros utilitaires PURH
% -----------------------------------------------------------------
\newcommand{{\PurhSubtitle}}[1]{{%
  \par\vspace{{0.4\baselineskip}}%
  {{\large\itshape #1\par}}%
  \vspace{{0.6\baselineskip}}%
}}

\newcommand{{\PurhContributors}}[1]{{%
  \par\vspace{{0.5\baselineskip}}%
  {{\normalsize\scshape #1\par}}%
  \vspace{{0.6\baselineskip}}%
}}

\newcommand{{\PurhTitleExtra}}[1]{{%
  {{\small #1\par}}%
}}

\newenvironment{{PurhBlockQuote}}
  {{%
    \begin{{quote}}\small
  }}
  {{%
    \end{{quote}}
  }}

\newenvironment{{PurhBibliography}}
  {{%
    \par
    \setlength{{\parindent}}{{0pt}}%
    \setlength{{\leftskip}}{{0pt}}%
  }}
  {{%
    \par
  }}
""".strip()


# ---------------------------------------------------------------------------
# Rendu global des parties du livre
# ---------------------------------------------------------------------------

    def _render_volume_title_page(self, book: Book) -> str:
        contributors = self._join_contributor_names(book.metadata.contributors)
        lines: list[str] = ["\\thispagestyle{empty}", "\\begin{center}", "\\vspace*{0.15\\textheight}"]
        lines.append(rf"{{\Huge\bfseries {self._escape_text(book.metadata.title)}\par}}")

        if book.metadata.subtitle:
            lines.append(rf"\PurhSubtitle{{{self._escape_text(book.metadata.subtitle)}}}")

        if contributors:
            lines.append(rf"\PurhContributors{{{self._escape_text(contributors)}}}")

        publication_line = self._volume_publication_line(book)
        if publication_line:
            lines.append(rf"\PurhTitleExtra{{{self._escape_text(publication_line)}}}")

        lines.extend(["\\vfill", "\\end{center}", "\\clearpage"])
        return "\n".join(lines)

    def _render_front_divisions(self, book: Book) -> str:
        return self._render_division_sequence(book.front_divisions, frontmatter=True)

    def _render_body_divisions(self, book: Book) -> str:
        return self._render_division_sequence(book.body_divisions, frontmatter=False)

    def _render_back_divisions(self, book: Book) -> str:
        return self._render_division_sequence(book.back_divisions, frontmatter=False, backmatter=True)

    def _render_division_sequence(
        self,
        divisions: list[Division],
        *,
        frontmatter: bool = False,
        backmatter: bool = False,
    ) -> str:
        rendered: list[str] = []
        for division in divisions:
            rendered.append(self._render_division(division, frontmatter=frontmatter, backmatter=backmatter))
        return "\n\n".join(part for part in rendered if part.strip())


# ---------------------------------------------------------------------------
# Divisions
# ---------------------------------------------------------------------------

    def _render_division(
        self,
        division: Division,
        *,
        frontmatter: bool = False,
        backmatter: bool = False,
    ) -> str:
        previous_notes = self._current_notes
        self._current_notes = division.notes
        try:
            lines: list[str] = []

            heading = self._render_division_heading(division, frontmatter=frontmatter, backmatter=backmatter)
            if heading:
                lines.append(heading)

            if division.title_page and division.div_type not in {DivisionType.PART}:
                contributor_block = self._render_division_titlepage_details(division.title_page)
                if contributor_block:
                    lines.append(contributor_block)

            blocks_and_sections = []
            blocks_and_sections.append(self._render_blocks(division.blocks))
            for section in division.sections:
                blocks_and_sections.append(self._render_section(section))
            if blocks_and_sections:
                lines.append("\n\n".join(chunk for chunk in blocks_and_sections if chunk.strip()))

            return "\n\n".join(chunk for chunk in lines if chunk.strip())
        finally:
            self._current_notes = previous_notes

    def _render_division_heading(
        self,
        division: Division,
        *,
        frontmatter: bool,
        backmatter: bool,
    ) -> str:
        title = division.title or (division.title_page.title if division.title_page else None)
        if not title:
            return ""

        escaped_title = self._escape_text(title)

        if division.div_type == DivisionType.PART:
            return (
                    rf"\part*{{{escaped_title}}}" + "\n"
                    + rf"\addcontentsline{{toc}}{{part}}{{{escaped_title}}}"
            )

        numbered = division.div_type == DivisionType.CHAPTER
        if numbered and not frontmatter and not backmatter:
            return rf"\chapter{{{escaped_title}}}"

        if division.div_type == DivisionType.APPENDIX and not self._appendix_started:
            self._appendix_started = True
            return (
                "\\appendix\n"
                rf"\chapter{{{escaped_title}}}"
            )

        # Par défaut, on reste non numéroté pour les liminaires et la plupart des post-liminaires.
        return (
                rf"\chapter*{{{escaped_title}}}" + "\n"
                + rf"\addcontentsline{{toc}}{{chapter}}{{{escaped_title}}}"
        )

    def _render_division_titlepage_details(self, title_page: TitlePageBlock) -> str:
        lines: list[str] = []

        if title_page.subtitle:
            lines.append(rf"\PurhSubtitle{{{self._escape_text(title_page.subtitle)}}}")

        contributors = self._join_contributor_names(title_page.contributors)
        if contributors:
            lines.append(rf"\PurhContributors{{{self._escape_text(contributors)}}}")

        for extra in title_page.extra_lines:
            if extra.strip():
                lines.append(rf"\PurhTitleExtra{{{self._escape_text(extra)}}}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

    def _render_section(self, section: Section) -> str:
        lines: list[str] = []
        title = self._escape_text(section.title)

        if section.level == 1:
            lines.append(rf"\section{{{title}}}")
        elif section.level == 2:
            lines.append(rf"\subsection{{{title}}}")
        else:
            lines.append(rf"\subsubsection{{{title}}}")

        if section.blocks:
            lines.append(self._render_blocks(section.blocks))
        for child in section.sections:
            lines.append(self._render_section(child))

        return "\n\n".join(chunk for chunk in lines if chunk.strip())


# ---------------------------------------------------------------------------
# Blocs
# ---------------------------------------------------------------------------

    def _render_blocks(self, blocks: Iterable[BlockNode]) -> str:
        rendered: list[str] = []
        for block in blocks:
            chunk = self._render_block(block)
            if chunk.strip():
                rendered.append(chunk)
        return "\n\n".join(rendered)

    def _render_block(self, block: BlockNode) -> str:
        if isinstance(block, Paragraph):
            return self._render_paragraph(block)
        if isinstance(block, QuoteBlock):
            return self._render_quote_block(block)
        if isinstance(block, FigureBlock):
            return self._render_figure_block(block)
        if isinstance(block, BibliographyBlock):
            return self._render_bibliography_block(block)
        if isinstance(block, ListBlock):
            return self._render_list_block(block)
        if isinstance(block, VerseBlock):
            return self._render_verse_block(block)
        if isinstance(block, TitlePageBlock):
            return self._render_division_titlepage_details(block)
        return ""

    def _render_paragraph(self, paragraph: Paragraph) -> str:
        content = self._render_inline_nodes(paragraph.content)
        if not content.strip():
            return ""

        if paragraph.render_hint == "signature":
            return rf"\begin{{flushright}}{content}\end{{flushright}}"
        if paragraph.render_hint == "lead":
            return rf"{{\noindent\bfseries {content}}}"
        if paragraph.render_hint == "break":
            return r"\bigskip"
        return content

    def _render_quote_block(self, quote_block: QuoteBlock) -> str:
        body = self._render_blocks(quote_block.blocks)
        source = self._render_inline_nodes(quote_block.source) if quote_block.source else ""

        lines = ["\\begin{PurhBlockQuote}", body]
        if source.strip():
            lines.append(rf"\par\raggedleft\small {source}")
        lines.append("\\end{PurhBlockQuote}")
        return "\n".join(chunk for chunk in lines if chunk.strip())

    def _render_figure_block(self, figure: FigureBlock) -> str:
        image_path = self._latex_path(figure.image_path)
        title = self._render_inline_nodes(figure.title) if figure.title else ""
        caption = self._render_inline_nodes(figure.caption) if figure.caption else ""
        credits = self._render_inline_nodes(figure.credits) if figure.credits else ""

        caption_parts: list[str] = []
        if title.strip():
            caption_parts.append(rf"\textbf{{{title}}}")
        if caption.strip():
            caption_parts.append(caption)

        full_caption = ". ".join(
            part.strip().rstrip(".") for part in caption_parts if part.strip()
        )

        lines = ["\\begin{center}"]

        if image_path and Path(image_path).exists():
            lines.append(
                rf"\includegraphics[width={self.options.figure_max_width},keepaspectratio]{{{image_path}}}"
            )
        else:
            lines.append(
                r"\fbox{\parbox{0.8\linewidth}{\centering\footnotesize Image absente ou non fournie}}"
            )

        if full_caption:
            lines.append(rf"\par\small {full_caption}")
        elif title.strip():
            lines.append(rf"\par\small \textbf{{{title}}}")

        if credits.strip():
            lines.append(rf"\par\footnotesize {credits}")

        lines.append("\\end{center}")
        return "\n".join(lines)

    def _render_bibliography_block(self, bibliography: BibliographyBlock) -> str:
        lines: list[str] = []

        if bibliography.title:
            title = self._escape_text(bibliography.title)
            lines.append(rf"\section*{{{title}}}")
            lines.append(rf"\addcontentsline{{toc}}{{section}}{{{title}}}")

        lines.append("\\begin{PurhBibliography}")
        for item in bibliography.items:
            lines.append(self._render_bibliography_item(item))
        lines.append("\\end{PurhBibliography}")
        return "\n".join(lines)

    def _render_bibliography_item(self, item: BibliographyItem) -> str:
        content = self._render_inline_nodes(item.content)
        if not content.strip():
            return ""
        hang = self.options.bibliography_hangindent_em
        return rf"\noindent\hangindent={hang}em\hangafter=1 {content}\par"

    def _render_list_block(self, list_block: ListBlock) -> str:
        env = "enumerate" if list_block.kind == ListKind.ORDERED else "itemize"
        lines = [rf"\begin{{{env}}}[leftmargin=*]"]
        for item in list_block.items:
            lines.append(self._render_list_item(item))
        lines.append(rf"\end{{{env}}}")
        return "\n".join(lines)

    def _render_list_item(self, item: ListItem) -> str:
        content = self._render_blocks(item.blocks)
        content = content.strip() or ""
        return rf"\item {content}"

    def _render_verse_block(self, verse_block: VerseBlock) -> str:
        lines = ["\\begin{verse}"]
        for verse_line in verse_block.lines:
            lines.append(self._render_verse_line(verse_line))
        lines.append("\\end{verse}")
        return "\n".join(lines)

    def _render_verse_line(self, verse_line: VerseLine) -> str:
        content = self._render_inline_nodes(verse_line.content)
        if verse_line.number:
            number = self._escape_text(verse_line.number)
            return rf"{content}\hfill{{\footnotesize {number}}}\\"
        return rf"{content}\\"


# ---------------------------------------------------------------------------
# Inline
# ---------------------------------------------------------------------------

    def _render_inline_nodes(self, nodes: Iterable[InlineNode] | None) -> str:
        if not nodes:
            return ""
        return "".join(self._render_inline_node(node) for node in nodes)

    def _render_inline_node(self, node: InlineNode) -> str:
        if isinstance(node, TextRun):
            return self._escape_text(node.text)
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
        if isinstance(node, Link):
            label = self._render_inline_nodes(node.children) or self._escape_text(node.target)
            target = self._escape_text(node.target)
            return rf"\href{{{target}}}{{{label}}}"
        if isinstance(node, InlineQuote):
            return rf"\enquote{{{self._render_inline_nodes(node.children)}}}"
        if isinstance(node, NoteRef):
            return self._render_note_ref(node)
        return ""

    def _render_note_ref(self, note_ref: NoteRef) -> str:
        if self._in_footnote:
            return r"\textsuperscript{*}"

        note = self._current_notes.get(note_ref.note_id)
        if note is None:
            missing = self._escape_text(note_ref.note_id)
            return rf"\footnote{{[Note introuvable : {missing}]}}"

        content = self._render_footnote_content(note)
        return rf"\footnote{{{content}}}"

    def _render_footnote_content(self, note: Footnote) -> str:
        previous_state = self._in_footnote
        self._in_footnote = True
        try:
            pieces: list[str] = []
            for block in note.blocks:
                rendered = self._render_block(block).strip()
                if rendered:
                    pieces.append(rendered)
            return r"\par ".join(pieces) if pieces else ""
        finally:
            self._in_footnote = previous_state


# ---------------------------------------------------------------------------
# Utilitaires éditoriaux et LaTeX
# ---------------------------------------------------------------------------

    def _volume_publication_line(self, book: Book) -> str:
        items: list[str] = []
        publication = book.metadata.publication
        if publication.publisher:
            items.append(publication.publisher)
        if publication.publication_year:
            items.append(publication.publication_year)
        return " · ".join(item for item in items if item)

    def _join_contributor_names(self, contributors) -> str:
        names = [c.full_name for c in contributors if getattr(c, "full_name", "").strip()]
        return " ; ".join(names)

    def _latex_path(self, path_value: str | None) -> str:
        if not path_value:
            return ""
        return str(Path(path_value).as_posix())

    def _escape_text(self, value: str | None) -> str:
        if value is None:
            return ""

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

        escaped = []
        for char in value:
            escaped.append(replacements.get(char, char))
        return "".join(escaped)


# ---------------------------------------------------------------------------
# Fonctions de confort
# ---------------------------------------------------------------------------


def render_book_to_latex(book: Book, options: LatexRenderOptions | None = None) -> str:
    """Fonction de confort pour produire le LaTeX en une ligne."""

    renderer = LatexRenderer(options=options)
    return renderer.render_book(book)
