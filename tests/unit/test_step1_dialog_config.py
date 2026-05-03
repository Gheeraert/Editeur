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
    build_step1_options_from_form,
    build_config_dict,
    decision_mode_from_label,
    decision_mode_to_label,
    derive_ai_flags_from_decision_mode,
    heuristic_profile_from_label,
    heuristic_profile_to_label,
    load_config_file,
    ai_aggressiveness_from_label,
    ai_aggressiveness_to_label,
    normalize_ai_aggressiveness,
    normalize_decision_mode,
    normalize_heuristic_profile,
    normalize_optional_threshold,
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
            decision_mode="heuristic",
            heuristic_profile="conservative",
            heading_transform_threshold=None,
            heading_diagnostic_threshold=None,
            poetry_transform_threshold=None,
            poetry_diagnostic_threshold=None,
            ai_aggressiveness="conservative",
            ai_provider="groq",
            ai_api_key="secret-key",
            ai_model="llama-x",
            ai_base_url="https://example.test/v1",
            enable_structure_ai=False,
            enable_editorial_ai=False,
            enable_ai=False,
            max_ai_calls=6,
            max_structure_ai_calls=6,
        )
        self.assertEqual(config["version"], 1)
        self.assertEqual(config["source_path"], "C:/src.docx")
        self.assertEqual(config["output_docx_path"], "C:/out.docx")
        self.assertEqual(config["tei_output_path"], "C:/out.xml")
        self.assertEqual(config["decision_mode"], "heuristic")
        self.assertEqual(config["heuristic_profile"], "conservative")
        self.assertEqual(config["ai_aggressiveness"], "conservative")
        self.assertEqual(config["ai_provider"], "groq")
        self.assertEqual(config["ai_api_key"], "secret-key")
        self.assertEqual(config["ai_model"], "llama-x")
        self.assertEqual(config["ai_base_url"], "https://example.test/v1")
        self.assertEqual(config["enable_structure_ai"], False)
        self.assertEqual(config["enable_editorial_ai"], False)
        self.assertEqual(config["enable_ai"], False)
        self.assertEqual(config["max_ai_calls"], 6)
        self.assertEqual(config["max_structure_ai_calls"], 6)
        self.assertEqual(config["export_json"], True)
        self.assertEqual(config["pivot_json_output_path"], "")

    def test_apply_config_dict_minimal_keeps_defaults(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", False, False, False, 6, 6)
        merged = apply_config_dict(current, {"version": 1, "source_path": "C:/a.docx"})
        self.assertEqual(merged["source_path"], "C:/a.docx")
        self.assertEqual(merged["output_docx_path"], "")
        self.assertEqual(merged["tei_output_path"], "")
        self.assertEqual(merged["decision_mode"], "heuristic")
        self.assertEqual(merged["heuristic_profile"], "conservative")
        self.assertEqual(merged["ai_aggressiveness"], "conservative")
        self.assertEqual(merged["ai_provider"], "groq")
        self.assertEqual(merged["ai_api_key"], "")
        self.assertEqual(merged["enable_structure_ai"], False)
        self.assertEqual(merged["enable_editorial_ai"], False)
        self.assertEqual(merged["enable_ai"], False)
        self.assertEqual(merged["max_ai_calls"], 6)
        self.assertEqual(merged["max_structure_ai_calls"], 6)
        self.assertEqual(merged["export_json"], True)
        self.assertEqual(merged["pivot_json_output_path"], "")

    def test_apply_config_dict_preserves_enable_ai_and_max_ai_calls(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", False, False, False, 6, 6)
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
            decision_mode="heuristic",
            heuristic_profile="balanced",
            heading_transform_threshold=0.85,
            heading_diagnostic_threshold=0.60,
            poetry_transform_threshold=0.90,
            poetry_diagnostic_threshold=0.65,
            ai_aggressiveness="balanced",
            ai_provider="groq",
            ai_api_key="api-key-clear",
            ai_model="llama-y",
            ai_base_url="https://example.test/v1",
            enable_structure_ai=False,
            enable_editorial_ai=False,
            enable_ai=False,
            max_ai_calls=6,
            max_structure_ai_calls=7,
        )
        save_config_file(path, config)
        raw = path.read_text(encoding="utf-8")
        self.assertIn('\n  "version": 1,', raw)
        loaded_json = json.loads(raw)
        self.assertEqual(loaded_json["source_path"], "C:/échantillon/source.docx")

        loaded = load_config_file(path)
        self.assertEqual(loaded["output_docx_path"], "C:/sortie.docx")

    def test_apply_config_dict_backward_compat_without_export_json(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", False, False, False, 6, 6)
        loaded = {"version": 1, "source_path": "C:/a.docx", "export_docx": True, "export_tei": True}
        merged = apply_config_dict(current, loaded)
        self.assertEqual(merged["export_json"], True)
        self.assertEqual(merged["pivot_json_output_path"], "")

    def test_config_roundtrip_preserves_export_json_and_pivot_json_output_path(self) -> None:
        path = self._runtime_path("step1_config_json_pivot")
        cfg = build_config_dict(
            source_path="C:/src.docx",
            output_docx_path="C:/out.docx",
            tei_output_path="C:/out.xml",
            decision_mode="heuristic",
            heuristic_profile="conservative",
            heading_transform_threshold=None,
            heading_diagnostic_threshold=None,
            poetry_transform_threshold=None,
            poetry_diagnostic_threshold=None,
            ai_aggressiveness="conservative",
            ai_provider="groq",
            ai_api_key="",
            ai_model="",
            ai_base_url="",
            enable_structure_ai=False,
            enable_editorial_ai=False,
            enable_ai=False,
            max_ai_calls=6,
            max_structure_ai_calls=6,
            export_json=False,
            pivot_json_output_path="C:/out/pivot.json",
        )
        save_config_file(path, cfg)
        loaded = load_config_file(path)
        merged = apply_config_dict(build_config_dict(), loaded)
        self.assertEqual(merged["export_json"], False)
        self.assertEqual(merged["pivot_json_output_path"], "C:/out/pivot.json")

    def test_decision_mode_heuristic_ai_local_sets_structure_ai_only(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", False, False, False, 6, 6)
        merged = apply_config_dict(current, {"decision_mode": "heuristic_ai_local"})
        self.assertEqual(merged["enable_structure_ai"], True)
        self.assertEqual(merged["enable_editorial_ai"], False)
        self.assertEqual(merged["enable_ai"], False)

    def test_decision_mode_heuristic_keeps_existing_editorial_toggle_when_not_explicit(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", True, True, True, 6, 6)
        merged = apply_config_dict(current, {"decision_mode": "heuristic"})
        self.assertEqual(merged["enable_structure_ai"], False)
        self.assertEqual(merged["enable_editorial_ai"], True)
        self.assertEqual(merged["enable_ai"], False)

    def test_decision_mode_heuristic_preserves_explicit_editorial_ai(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", False, False, False, 6, 6)
        merged = apply_config_dict(
            current,
            {"decision_mode": "heuristic", "enable_editorial_ai": True},
        )
        self.assertEqual(merged["enable_structure_ai"], False)
        self.assertEqual(merged["enable_editorial_ai"], True)
        self.assertEqual(merged["enable_ai"], False)

    def test_decision_mode_deterministic_disables_ais(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", True, True, True, 6, 6)
        merged = apply_config_dict(current, {"decision_mode": "deterministic", "enable_editorial_ai": True})
        self.assertEqual(merged["enable_structure_ai"], False)
        self.assertEqual(merged["enable_editorial_ai"], False)
        self.assertEqual(merged["enable_ai"], False)

    def test_decision_mode_ai_exploratory_keeps_safe_fallback(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", True, True, True, 6, 6)
        merged = apply_config_dict(current, {"decision_mode": "ai_exploratory"})
        self.assertEqual(merged["enable_structure_ai"], False)
        self.assertEqual(merged["enable_editorial_ai"], False)
        self.assertEqual(merged["enable_ai"], False)

    def test_heuristic_profile_and_overrides_are_kept(self) -> None:
        current = build_config_dict("", "", "", "heuristic", "conservative", None, None, None, None, "conservative", "groq", "", "", "", False, False, False, 6, 6)
        merged = apply_config_dict(
            current,
            {
                "heuristic_profile": "exploratory",
                "heading_transform_threshold": 0.77,
                "heading_diagnostic_threshold": 0.52,
                "poetry_transform_threshold": 0.83,
                "poetry_diagnostic_threshold": 0.57,
            },
        )
        self.assertEqual(merged["heuristic_profile"], "exploratory")
        self.assertEqual(merged["heading_transform_threshold"], 0.77)
        self.assertEqual(merged["heading_diagnostic_threshold"], 0.52)
        self.assertEqual(merged["poetry_transform_threshold"], 0.83)
        self.assertEqual(merged["poetry_diagnostic_threshold"], 0.57)

    def test_ai_aggressiveness_normalization(self) -> None:
        self.assertEqual(normalize_ai_aggressiveness("conservative"), "conservative")
        self.assertEqual(normalize_ai_aggressiveness("balanced"), "balanced")
        self.assertEqual(normalize_ai_aggressiveness("aggressive"), "aggressive")
        self.assertEqual(normalize_ai_aggressiveness("weird"), "conservative")

    def test_heuristic_profile_normalization(self) -> None:
        self.assertEqual(normalize_heuristic_profile("conservative"), "conservative")
        self.assertEqual(normalize_heuristic_profile("balanced"), "balanced")
        self.assertEqual(normalize_heuristic_profile("exploratory"), "exploratory")
        self.assertEqual(normalize_heuristic_profile("weird"), "conservative")

    def test_optional_threshold_normalization(self) -> None:
        self.assertEqual(normalize_optional_threshold(""), None)
        self.assertEqual(normalize_optional_threshold(None), None)
        self.assertEqual(normalize_optional_threshold(0.8), 0.8)
        self.assertEqual(normalize_optional_threshold(2.0), 1.0)
        self.assertEqual(normalize_optional_threshold(-1.0), 0.0)

    def test_decision_mode_normalization(self) -> None:
        self.assertEqual(normalize_decision_mode("heuristic"), "heuristic")
        self.assertEqual(normalize_decision_mode("heuristic_ai_local"), "heuristic_ai_local")
        self.assertEqual(normalize_decision_mode("deterministic"), "deterministic")
        self.assertEqual(normalize_decision_mode("ai_exploratory"), "ai_exploratory")
        self.assertEqual(normalize_decision_mode("unknown"), "heuristic")

    def test_derive_ai_flags_from_decision_mode(self) -> None:
        self.assertEqual(derive_ai_flags_from_decision_mode("heuristic_ai_local"), (True, False))
        self.assertEqual(derive_ai_flags_from_decision_mode("heuristic"), (False, False))
        self.assertEqual(derive_ai_flags_from_decision_mode("deterministic"), (False, False))
        self.assertEqual(derive_ai_flags_from_decision_mode("ai_exploratory"), (False, False))

    def test_api_key_is_kept_in_clear_in_config_dict(self) -> None:
        cfg = build_config_dict(
            source_path="",
            output_docx_path="",
            tei_output_path="",
            decision_mode="heuristic",
            heuristic_profile="conservative",
            heading_transform_threshold=None,
            heading_diagnostic_threshold=None,
            poetry_transform_threshold=None,
            poetry_diagnostic_threshold=None,
            ai_aggressiveness="conservative",
            ai_provider="groq",
            ai_api_key="clear-text-key",
            ai_model="",
            ai_base_url="",
            enable_structure_ai=False,
            enable_editorial_ai=False,
            enable_ai=False,
            max_ai_calls=6,
            max_structure_ai_calls=6,
        )
        self.assertEqual(cfg["ai_api_key"], "clear-text-key")

    def test_label_mappings_roundtrip(self) -> None:
        self.assertEqual(decision_mode_from_label("Déterministe strict"), "deterministic")
        self.assertEqual(decision_mode_to_label("heuristic_ai_local"), "Heuristique + IA locale")
        self.assertEqual(heuristic_profile_from_label("Équilibré"), "balanced")
        self.assertEqual(heuristic_profile_to_label("exploratory"), "Exploratoire")
        self.assertEqual(ai_aggressiveness_from_label("Conservatrice"), "conservative")
        self.assertEqual(ai_aggressiveness_to_label("aggressive"), "Agressive")

    def test_build_step1_options_from_form_heuristic_ai_local(self) -> None:
        options = build_step1_options_from_form(
            decision_mode_label="Heuristique + IA locale",
            heuristic_profile_label="Prudent",
            heading_transform_threshold="",
            heading_diagnostic_threshold="",
            poetry_transform_threshold="",
            poetry_diagnostic_threshold="",
            ai_aggressiveness_label="Conservatrice",
            ai_provider="groq",
            ai_api_key="",
            ai_model="",
            ai_base_url="",
            enable_editorial_ai=False,
            max_ai_calls=6,
            max_structure_ai_calls=6,
            output_path=None,
            tei_output_path=None,
        )
        self.assertEqual(options.decision_mode, "heuristic_ai_local")
        self.assertTrue(options.enable_structure_ai)
        self.assertFalse(options.enable_editorial_ai)
        self.assertIsNone(options.heading_transform_threshold)

    def test_build_step1_options_from_form_editorial_toggle(self) -> None:
        options = build_step1_options_from_form(
            decision_mode_label="Heuristique",
            heuristic_profile_label="Équilibré",
            heading_transform_threshold="0.82",
            heading_diagnostic_threshold="0.55",
            poetry_transform_threshold="0.88",
            poetry_diagnostic_threshold="0.57",
            ai_aggressiveness_label="Équilibrée",
            ai_provider="groq",
            ai_api_key="secret",
            ai_model="model-x",
            ai_base_url="https://example.test",
            enable_editorial_ai=True,
            max_ai_calls=7,
            max_structure_ai_calls=5,
            output_path=None,
            tei_output_path=None,
        )
        self.assertEqual(options.decision_mode, "heuristic")
        self.assertFalse(options.enable_structure_ai)
        self.assertTrue(options.enable_editorial_ai)
        self.assertEqual(options.heading_transform_threshold, 0.82)
        self.assertEqual(options.heading_diagnostic_threshold, 0.55)
        self.assertEqual(options.poetry_transform_threshold, 0.88)
        self.assertEqual(options.poetry_diagnostic_threshold, 0.57)

    def test_build_step1_options_from_form_deterministic_disables_ias(self) -> None:
        options = build_step1_options_from_form(
            decision_mode_label="Déterministe strict",
            heuristic_profile_label="Prudent",
            heading_transform_threshold="",
            heading_diagnostic_threshold="",
            poetry_transform_threshold="",
            poetry_diagnostic_threshold="",
            ai_aggressiveness_label="Conservatrice",
            ai_provider="groq",
            ai_api_key="",
            ai_model="",
            ai_base_url="",
            enable_editorial_ai=False,
            max_ai_calls=6,
            max_structure_ai_calls=6,
            output_path=None,
            tei_output_path=None,
        )
        self.assertEqual(options.decision_mode, "deterministic")
        self.assertFalse(options.enable_structure_ai)
        self.assertFalse(options.enable_editorial_ai)


if __name__ == "__main__":
    unittest.main()
