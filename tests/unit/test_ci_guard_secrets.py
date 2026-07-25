from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("ci_guard", ROOT / "scripts" / "ci_guard.py")
ci_guard = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(ci_guard)


class CheckNoSecretsTrackedTests(unittest.TestCase):
    def _write(self, tmp_path: Path, relative: str, content: str) -> None:
        full = tmp_path / relative
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    def setUp(self) -> None:
        self._orig_root = ci_guard.ROOT

    def tearDown(self) -> None:
        ci_guard.ROOT = self._orig_root

    def test_env_file_tracked_is_rejected(self) -> None:
        errors = ci_guard.check_no_secrets_tracked([".env"])
        self.assertTrue(any(".env" in e for e in errors))

    def test_env_example_is_allowed(self) -> None:
        errors = ci_guard.check_no_secrets_tracked([".env.example"])
        self.assertEqual(errors, [])

    def test_pem_filename_suffix_is_rejected(self) -> None:
        errors = ci_guard.check_no_secrets_tracked(["certs/server.pem"])
        self.assertTrue(any("server.pem" in e for e in errors))

    def test_ssh_private_key_filename_is_rejected(self) -> None:
        errors = ci_guard.check_no_secrets_tracked(["id_rsa"])
        self.assertTrue(any("id_rsa" in e for e in errors))

    def test_groq_key_value_in_tracked_file_is_detected(self, tmp_path: Path | None = None) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "config.txt", "GROQ_API_KEY=gsk_" + "a" * 40)
            ci_guard.ROOT = tmp_path
            errors = ci_guard.check_no_secrets_tracked(["config.txt"])
            self.assertTrue(any("Groq" in e for e in errors))
            # La valeur complète ne doit jamais apparaître en clair dans le message.
            self.assertNotIn("gsk_" + "a" * 40, "\n".join(errors))

    def test_openai_key_value_is_detected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "config.txt", "OPENAI_API_KEY=sk-" + "b" * 40)
            ci_guard.ROOT = tmp_path
            errors = ci_guard.check_no_secrets_tracked(["config.txt"])
            self.assertTrue(any("OpenAI" in e for e in errors))

    def test_pem_private_key_content_is_detected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pem_header = "-----BEGIN " + "PRIVATE KEY-----"
            pem_footer = "-----END " + "PRIVATE KEY-----"
            self._write(tmp_path, "config.txt", f"{pem_header}\nabc\n{pem_footer}")
            ci_guard.ROOT = tmp_path
            errors = ci_guard.check_no_secrets_tracked(["config.txt"])
            self.assertTrue(any("PEM" in e for e in errors))

    def test_ordinary_file_without_secret_is_accepted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "README.md", "Ceci est un fichier normal sans secret.")
            ci_guard.ROOT = tmp_path
            errors = ci_guard.check_no_secrets_tracked(["README.md"])
            self.assertEqual(errors, [])

    def test_mask_never_reveals_full_secret(self) -> None:
        secret = "gsk_" + "x" * 40
        masked = ci_guard._mask(secret)
        self.assertNotIn(secret, masked)
        self.assertIn("…", masked)


if __name__ == "__main__":
    unittest.main()
