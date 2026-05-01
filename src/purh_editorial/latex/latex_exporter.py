from __future__ import annotations

from pathlib import Path

from purh_editorial.latex.latex_renderer import LatexRenderer
from purh_editorial.latex.tei_to_semantic import parse_tei_to_semantic


def export_tei_to_latex(input_xml: Path, output_tex: Path) -> Path:
    book = parse_tei_to_semantic(input_xml)
    renderer = LatexRenderer()
    return renderer.write_book(book, output_tex)
