from __future__ import annotations

import argparse
from pathlib import Path

from purh_editorial.latex.latex_renderer import LatexRenderer
from purh_editorial.latex.tei_loader import load_tei_tree
from purh_editorial.latex.tei_normalizer import normalize_tei_tree
from purh_editorial.latex.tei_to_semantic import parse_tei_tree_to_semantic


def export_tei_to_latex(input_xml: Path, output_tex: Path) -> Path:
    tree = load_tei_tree(input_xml)
    normalize_tei_tree(tree)
    book = parse_tei_tree_to_semantic(tree, fallback_title=input_xml.stem)
    renderer = LatexRenderer()
    return renderer.write_book(book, output_tex)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export XML-TEI to LaTeX (.tex).")
    parser.add_argument("input_xml", type=Path, help="Path to input TEI XML file.")
    parser.add_argument("output_tex", type=Path, help="Path to output .tex file.")
    args = parser.parse_args(argv)

    export_tei_to_latex(args.input_xml, args.output_tex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
