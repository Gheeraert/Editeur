from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.ai_editorial_service import AICorrection, AIEditorialService


class AIEditorialSuggestionsTests(unittest.TestCase):
    def _service(self) -> AIEditorialService:
        service = AIEditorialService(api_key="test", model="test-model", base_url="https://example.test")
        service._call_api = lambda *_args, **_kwargs: [AICorrection("erreur erreur", "erreur", "répétition")]  # type: ignore[method-assign]
        return service

    def test_ai_returns_reviewable_suggestion_without_mutating_text(self) -> None:
        text = ("Texte de démonstration. " * 12) + "erreur erreur dans cette phrase."
        document = Document("doc", "fixture", "txt", blocks=[Paragraph(block_id="p1", text=text)])

        returned, suggestions = self._service().apply(document)

        self.assertIs(returned, document)
        self.assertEqual(document.blocks[0].text, text)
        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion.target_ref, "p1")
        self.assertEqual(suggestion.proposed_text, "erreur")
        self.assertEqual(suggestion.attributes["before"], "erreur erreur")
        self.assertEqual(suggestion.attributes["after_proposed"], "erreur")
        self.assertEqual(suggestion.attributes["status"], "pending_human_review")
        self.assertEqual(suggestion.attributes["rule_id"], "purh.ai.editorial")

    def test_ai_does_not_submit_or_suggest_protected_blocks(self) -> None:
        text = ("Texte protégé. " * 20) + "erreur erreur."
        document = Document(
            "doc", "fixture", "txt",
            blocks=[Paragraph(block_id="p1", text=text, attributes={"protected_zone": "quote"})],
        )
        service = self._service()

        _returned, suggestions = service.apply(document)

        self.assertEqual(suggestions, [])
