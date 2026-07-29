from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from purh_editorial.services.word_review_service import WordReviewError
from purh_editorial.services.word_workspace_service import WordWorkspaceState
from purh_editorial import word_workspace


class _PythonCom:
    def __init__(self) -> None:
        self.initialized = self.uninitialized = self.pumped = 0

    def CoInitialize(self) -> None: self.initialized += 1
    def CoUninitialize(self) -> None: self.uninitialized += 1
    def PumpWaitingMessages(self) -> None: self.pumped += 1


class _Session:
    def __init__(self, original: Path, review: Path) -> None:
        self.app = mock.Mock()
        self.app.Documents.Count = 0
        self.quit_called = 0
        self.state = WordWorkspaceState(original, review, True, False, True, True, True, "positional_simple", [], [])
    def quit_application(self) -> None: self.quit_called += 1


class WordWorkspaceCliTests(unittest.TestCase):
    def test_writes_ready_file_and_initializes_com(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            original, review, ready = (Path(root) / name for name in ("original.docx", "review.docx", "ready.json"))
            original.write_bytes(b"x"); review.write_bytes(b"x")
            session = _Session(original, review); pythoncom = _PythonCom()
            with mock.patch.dict(sys.modules, {"pythoncom": pythoncom}), mock.patch.object(
                word_workspace, "WordWorkspaceService"
            ) as service:
                service.return_value.open_workspace.return_value = session
                code = word_workspace.main([str(original), str(review), "--ready-file", str(ready)])
            self.assertEqual(code, 0)
            self.assertEqual((pythoncom.initialized, pythoncom.uninitialized), (1, 1))
            self.assertTrue(pythoncom.pumped >= 1)
            self.assertEqual(json.loads(ready.read_text(encoding="utf-8"))["status"], "ready")
            self.assertEqual(session.quit_called, 1)

    def test_writes_error_file_before_returning_failure(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            original, review, ready = (Path(root) / name for name in ("original.docx", "review.docx", "ready.json"))
            pythoncom = _PythonCom()
            with mock.patch.dict(sys.modules, {"pythoncom": pythoncom}), mock.patch.object(
                word_workspace, "WordWorkspaceService"
            ) as service:
                service.return_value.open_workspace.side_effect = WordReviewError("Word indisponible")
                code = word_workspace.main([str(original), str(review), "--ready-file", str(ready)])
            self.assertEqual(code, 1)
            payload = json.loads(ready.read_text(encoding="utf-8"))
            self.assertEqual(payload, {"status": "error", "message": "Word indisponible"})
            self.assertEqual((pythoncom.initialized, pythoncom.uninitialized), (1, 1))


if __name__ == "__main__":
    unittest.main()
