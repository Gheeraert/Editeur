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
    args = parser.parse_args()

    try:
        counts = correct_docx(args.input_path, args.output_path)
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

