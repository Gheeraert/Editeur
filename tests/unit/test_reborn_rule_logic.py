from purh_editorial.corrector.rules.footnotes import (
    NNBSP,
    normalize_op_cit_spacing,
)
from purh_editorial.corrector.rules.orthotypography import (
    find_centuries,
    normalize_points_suspension,
)


def test_points_suspension_exact_sequence() -> None:
    assert normalize_points_suspension("Texte... Suite") == "Texte… Suite"
    assert normalize_points_suspension("Texte….") == "Texte…."
    assert normalize_points_suspension("Texte… Suite") == "Texte… Suite"
    assert normalize_points_suspension("Texte.... Suite") == "Texte.... Suite"


def test_century_closed_domain_and_context() -> None:
    for text in ("XVIème siècle", "xvie siècle", "VIe siècle", "Ier siècle"):
        assert len(find_centuries(text)) == 1

    for text in (
        "la vie continue",
        "une vie entière",
        "VIe",
        "XVIème chapitre",
        "XLIVe siècle",
    ):
        assert find_centuries(text) == []


def test_century_normalized_text() -> None:
    assert find_centuries("XVIème siècle")[0].normalized == "xvie"
    assert find_centuries("Ier siècle")[0].normalized == "ier"


def test_op_cit_spacing() -> None:
    assert normalize_op_cit_spacing("Voir op. cit.") == f"Voir op.{NNBSP}cit."
    assert normalize_op_cit_spacing("Voir art.  cit.") == f"Voir art.{NNBSP}cit."
    assert normalize_op_cit_spacing("Voir loc.") == "Voir loc."
    normalized = f"Voir loc.{NNBSP}cit."
    assert normalize_op_cit_spacing(normalized) == normalized

