from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.pipeline.step1 import Step1Options


class Step1OptionsDecisionModeTests(unittest.TestCase):
    def test_heuristic_ai_local_enables_structure_ai_only(self) -> None:
        options = Step1Options(decision_mode="heuristic_ai_local")
        self.assertTrue(options.structure_ai_enabled())
        self.assertFalse(options.editorial_ai_enabled())

    def test_heuristic_mode_disables_ia(self) -> None:
        options = Step1Options(decision_mode="heuristic")
        self.assertFalse(options.structure_ai_enabled())
        self.assertFalse(options.editorial_ai_enabled())

    def test_deterministic_mode_disables_ia(self) -> None:
        options = Step1Options(decision_mode="deterministic")
        self.assertFalse(options.structure_ai_enabled())
        self.assertFalse(options.editorial_ai_enabled())

    def test_ai_exploratory_mode_keeps_safe_fallback(self) -> None:
        options = Step1Options(decision_mode="ai_exploratory")
        self.assertFalse(options.structure_ai_enabled())
        self.assertFalse(options.editorial_ai_enabled())
        self.assertTrue(options.exploratory_mode_requested())

    def test_legacy_enable_ai_still_controls_editorial_when_mode_not_set(self) -> None:
        options = Step1Options(enable_ai=True, decision_mode=None)
        self.assertTrue(options.editorial_ai_enabled())
        self.assertFalse(options.structure_ai_enabled())


if __name__ == "__main__":
    unittest.main()

