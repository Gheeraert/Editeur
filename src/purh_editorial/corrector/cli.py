from __future__ import annotations

import argparse
from pathlib import Path

from purh_editorial.corrector import correct_docx


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corrige une copie d'un document DOCX avec Microsoft Word."
    )
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument(
        "--reapply-normal-style",
        action="store_true",
        help=(
            "Réapplique le style 'Normal' à chaque paragraphe qui le porte déjà "
            "(contournement d'un artefact de rendu Word). Désactivé par défaut."
        ),
    )
    args = parser.parse_args()

    try:
        counts = correct_docx(
            args.input_path,
            args.output_path,
            reapply_normal_style=args.reapply_normal_style,
        )
    except Exception as exc:
        parser.exit(1, f"Erreur : {exc}\n")

    print(f"Document corrigé : {args.output_path}")
    print(f"Total des corrections : {sum(counts.values())}")
    for rule_id, count in counts.items():
        if count:
            print(f"{rule_id}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

