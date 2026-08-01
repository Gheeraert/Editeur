from __future__ import annotations

from purh_editorial.corrector.ai import LocatedAISuggestion
from purh_editorial.corrector.word_document import WD_DARK_YELLOW, _format_ai_comment


def test_wd_dark_yellow_is_distinct_from_other_traceability_colors() -> None:
    from purh_editorial.corrector.word_document import (
        WD_BRIGHT_GREEN,
        WD_TURQUOISE,
        WD_YELLOW,
    )

    colors = {WD_YELLOW, WD_TURQUOISE, WD_BRIGHT_GREEN, WD_DARK_YELLOW}
    assert len(colors) == 4


def test_format_ai_comment_includes_rule_id_explanation_and_suggestion() -> None:
    suggestion = LocatedAISuggestion(
        rule_id="ia.style.lourdeur",
        start=0,
        end=10,
        original_text="il s'avère avéré",
        suggested_text="il est avéré",
        explanation="Pléonasme.",
    )
    comment = _format_ai_comment(suggestion)
    assert "ia.style.lourdeur" in comment
    assert "Pléonasme." in comment
    assert "il est avéré" in comment
    # Le texte original n'a pas vocation à réapparaître dans le commentaire :
    # il est déjà visible dans le document via le surlignage.
    assert "il s'avère avéré" not in comment
