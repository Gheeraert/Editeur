from __future__ import annotations

import argparse
from pathlib import Path

from purh_editorial.services.word_review_service import WordReviewError, WordReviewService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cree un DOCX de revision par comparaison native Microsoft Word.",
    )
    parser.add_argument("original", type=Path, help="DOCX original")
    parser.add_argument("candidate", type=Path, help="DOCX candidat corrige")
    parser.add_argument("revision", type=Path, help="DOCX de revision a produire")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = WordReviewService().create_review_document(
            original_path=args.original,
            revised_path=args.candidate,
            output_path=args.revision,
        )
    except WordReviewError as exc:
        parser.exit(1, f"Erreur : {exc}\n")

    tracked = "oui" if result.has_tracked_changes else "non"
    print(f"Document de revision cree : {result.output_path}")
    print(f"Modifications suivies detectees : {tracked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
