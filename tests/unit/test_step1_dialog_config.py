from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.ui.step1_dialog import (
    apply_config_dict,
    build_config_dict,
    load_config_file,
    save_config_file,
)


class Step1DialogConfigTests(unittest.TestCase):
    @staticmethod
    def _runtime_path(name: str) -> Path:
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / f"{name}_{uuid.uuid4().hex}.json"

    def test_build_config_dict_complete(self) -> None:
        config = build_config_dict(
            source_path="C:/src.docx",
            output_docx_path="C:/out.docx",
            tei_output_path="C:/out.xml",
            enable_ai=False,
            max_ai_calls=6,
        )
        self.assertEqual(config["version"], 1)
        self.assertEqual(config["source_path"], "C:/src.docx")
        self.assertEqual(config["output_docx_path"], "C:/out.docx")
        self.assertEqual(config["tei_output_path"], "C:/out.xml")
        self.assertEqual(config["enable_ai"], False)
        self.assertEqual(config["max_ai_calls"], 6)

    def test_apply_config_dict_minimal_keeps_defaults(self) -> None:
        current = build_config_dict("", "", "", False, 6)
        merged = apply_config_dict(current, {"version": 1, "source_path": "C:/a.docx"})
        self.assertEqual(merged["source_path"], "C:/a.docx")
        self.assertEqual(merged["output_docx_path"], "")
        self.assertEqual(merged["tei_output_path"], "")
        self.assertEqual(merged["enable_ai"], False)
        self.assertEqual(merged["max_ai_calls"], 6)

    def test_apply_config_dict_preserves_enable_ai_and_max_ai_calls(self) -> None:
        current = build_config_dict("", "", "", False, 6)
        merged = apply_config_dict(current, {"enable_ai": True, "max_ai_calls": 12})
        self.assertEqual(merged["enable_ai"], True)
        self.assertEqual(merged["max_ai_calls"], 12)

    def test_load_config_file_invalid_json_raises_clear_error(self) -> None:
        path = self._runtime_path("invalid")
        path.write_text("{invalid", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "JSON invalide"):
            load_config_file(path)

    def test_save_and_load_roundtrip_utf8_indented(self) -> None:
        path = self._runtime_path("step1_config")
        config = build_config_dict(
            source_path="C:/échantillon/source.docx",
            output_docx_path="C:/sortie.docx",
            tei_output_path="C:/sortie.xml",
            enable_ai=False,
            max_ai_calls=6,
        )
        save_config_file(path, config)
        raw = path.read_text(encoding="utf-8")
        self.assertIn('\n  "version": 1,', raw)
        loaded_json = json.loads(raw)
        self.assertEqual(loaded_json["source_path"], "C:/échantillon/source.docx")

        loaded = load_config_file(path)
        self.assertEqual(loaded["output_docx_path"], "C:/sortie.docx")


if __name__ == "__main__":
    unittest.main()
