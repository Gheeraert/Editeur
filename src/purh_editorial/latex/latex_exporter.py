from __future__ import annotations

import argparse
import shutil
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
    result = renderer.write_book(book, output_tex)

    # Les figures référencent media/... : copier le bundle média du TEI à côté du
    # .tex, faute de quoi \includegraphics pointerait vers un fichier absent.
    source_media_dir = input_xml.parent / "media"
    if source_media_dir.is_dir():
        dest_media_dir = output_tex.parent / "media"
        dest_media_dir.mkdir(parents=True, exist_ok=True)
        for media_file in source_media_dir.iterdir():
            if media_file.is_file():
                shutil.copyfile(media_file, dest_media_dir / media_file.name)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export XML-TEI to LaTeX (.tex).")
    parser.add_argument("input_xml", type=Path, help="Path to input TEI XML file.")
    parser.add_argument("output_tex", type=Path, help="Path to output .tex file.")
    args = parser.parse_args(argv)

    export_tei_to_latex(args.input_xml, args.output_tex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
