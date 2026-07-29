from __future__ import annotations

import argparse
import time
from pathlib import Path

from purh_editorial.services.word_workspace_service import WordWorkspaceService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path); parser.add_argument("review", type=Path)
    args = parser.parse_args()
    app = WordWorkspaceService().open_workspace(original_path=args.original, review_path=args.review)
    while app.Documents.Count:
        time.sleep(0.5)
    app.Quit()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
