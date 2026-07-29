from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from purh_editorial.services.word_review_service import WordReviewError
from purh_editorial.services.word_workspace_service import WordWorkspaceService


def _write_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False)
        os.replace(name, path)
    except Exception:
        try:
            Path(name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _ready_payload(session) -> dict[str, object]:
    state = session.state
    return {
        "status": "ready",
        "original": str(state.original_path),
        "review": str(state.review_path),
        "original_read_only": state.original_read_only,
        "review_read_only": state.review_read_only,
        "original_on_left": state.original_on_left,
        "side_by_side_established": state.side_by_side_established,
        "side_by_side_strategy": state.side_by_side_strategy,
        "side_by_side_attempts": [
            {
                "strategy": item.strategy,
                "succeeded": item.succeeded,
                "return_value": item.return_value,
                "error_type": item.error_type,
                "error_message": item.error_message,
                "hresult": item.hresult,
            }
            for item in state.side_by_side_attempts
        ],
        "synchronized_scrolling": state.synchronized_scrolling,
        "warnings": state.warnings,
    }


def _wait_for_workspace(session, pythoncom) -> None:
    while True:
        pythoncom.PumpWaitingMessages()
        try:
            count = session.app.Documents.Count
        except Exception:
            return
        if count == 0:
            return
        time.sleep(0.25)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("--ready-file", type=Path)
    args = parser.parse_args(argv)
    try:
        import pythoncom
    except ImportError as exc:
        message = "pywin32 est requis pour ouvrir l’espace de relecture Word."
        if args.ready_file:
            _write_state(args.ready_file, {"status": "error", "message": message})
        print(message, file=sys.stderr)
        return 1

    pythoncom.CoInitialize()
    session = None
    try:
        session = WordWorkspaceService().open_workspace(
            original_path=args.original,
            review_path=args.review,
        )
        if args.ready_file:
            payload = _ready_payload(session)
            payload["status"] = "ready" if session.state.synchronized_scrolling else "partial"
            _write_state(args.ready_file, payload)
        _wait_for_workspace(session, pythoncom)
        try:
            if session.app.Documents.Count == 0:
                session.quit_application()
        except Exception:
            pass
        return 0
    except WordReviewError as exc:
        if args.ready_file:
            _write_state(args.ready_file, {"status": "error", "message": str(exc)})
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
