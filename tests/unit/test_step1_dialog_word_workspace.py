from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from purh_editorial.ui import step1_dialog


class _Status:
    def __init__(self) -> None: self.values: list[str] = []
    def set(self, value: str) -> None: self.values.append(value)


class _DialogHarness:
    def __init__(self) -> None:
        self._workspace_launch = None
        self._status = _Status()
        self.after_calls: list[tuple[int, object]] = []
    def after(self, delay, callback): self.after_calls.append((delay, callback))
    _launch_word_workspace = step1_dialog.Step1Dialog._launch_word_workspace
    _poll_word_workspace = step1_dialog.Step1Dialog._poll_word_workspace
    _finish_workspace_launch = step1_dialog.Step1Dialog._finish_workspace_launch


class Step1DialogWordWorkspaceTests(unittest.TestCase):
    def test_launch_command_waits_for_ready_instead_of_claiming_success(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            dialog = _DialogHarness(); original = Path(root) / "o.docx"; review = Path(root) / "r.docx"
            process = mock.Mock(); process.poll.return_value = None
            with mock.patch.object(step1_dialog.subprocess, "Popen", return_value=process) as popen:
                dialog._launch_word_workspace(original, review)
            command = popen.call_args.args[0]
            self.assertEqual(command[:3], [step1_dialog.sys.executable, "-m", "purh_editorial.word_workspace"])
            self.assertIn("--ready-file", command)
            self.assertIn("Ouverture", dialog._status.values[-1])
            self.assertNotIn("ouvert.", dialog._status.values[-1])
            ready = dialog._workspace_launch[1]
            ready.write_text(json.dumps({"status": "ready"}), encoding="utf-8")
            dialog._poll_word_workspace()
            self.assertEqual(dialog._status.values[-1], "Espace de relecture Word ouvert.")
            self.assertIsNone(dialog._workspace_launch)
            self.assertFalse(ready.exists())

    def test_error_ready_file_is_reported_without_deleting_documents(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            dialog = _DialogHarness(); ready = Path(root) / "ready.json"; ready.write_text(json.dumps({"status": "error", "message": "échec"}), encoding="utf-8")
            dialog._workspace_launch = (mock.Mock(), ready, 0)
            with mock.patch.object(step1_dialog.messagebox, "showerror") as showerror:
                dialog._poll_word_workspace()
            showerror.assert_called_once()
            self.assertIsNone(dialog._workspace_launch)
            self.assertFalse(ready.exists())


if __name__ == "__main__":
    unittest.main()
