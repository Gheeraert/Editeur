from __future__ import annotations

import pytest

from purh_editorial.rules.thresholds import (
    CanonicalThresholdPolicy,
    InvalidInterventionLevelError,
    UncalibratedScoreFamilyError,
)


@pytest.mark.parametrize(
    ("family", "level", "review", "apply"),
    [
        ("heading", 0, 0.70, 0.90),
        ("heading", 50, 0.60, 0.85),
        ("heading", 100, 0.50, 0.75),
        ("poetry", 0, 0.60, 0.82),
        ("poetry", 50, 0.55, 0.78),
        ("poetry", 100, 0.48, 0.72),
    ],
)
def test_historical_anchors_are_exact(
    family: str,
    level: int,
    review: float,
    apply: float,
) -> None:
    result = CanonicalThresholdPolicy().thresholds(
        score_family=family,
        intervention_level=level,
    )
    assert result.review == review
    assert result.apply == apply


@pytest.mark.parametrize(
    ("family", "level", "review", "apply"),
    [
        ("heading", 25, 0.65, 0.875),
        ("heading", 75, 0.55, 0.80),
        ("poetry", 25, 0.575, 0.80),
        ("poetry", 75, 0.515, 0.75),
    ],
)
def test_piecewise_linear_interpolation(
    family: str,
    level: int,
    review: float,
    apply: float,
) -> None:
    result = CanonicalThresholdPolicy().thresholds(
        score_family=family,
        intervention_level=level,
    )
    assert result.review == pytest.approx(review)
    assert result.apply == pytest.approx(apply)
    assert 0 <= result.review <= result.apply <= 1


def test_families_are_calibrated_independently() -> None:
    policy = CanonicalThresholdPolicy()
    heading = policy.thresholds(score_family="heading", intervention_level=25)
    poetry = policy.thresholds(score_family="poetry", intervention_level=25)
    assert heading != poetry


@pytest.mark.parametrize("level", [-1, 101, True, False, 1.5, "50", None])
def test_native_intervention_level_is_strict(level: object) -> None:
    with pytest.raises(InvalidInterventionLevelError):
        CanonicalThresholdPolicy().thresholds(
            score_family="heading",
            intervention_level=level,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "family",
    [
        "unknown",
        "footnote_form",
        "bibliography_structure",
        "bibliography_form",
        "quote_structure",
        "epigraph",
    ],
)
def test_uncalibrated_families_are_explicitly_refused(family: str) -> None:
    with pytest.raises(UncalibratedScoreFamilyError, match="uncalibrated"):
        CanonicalThresholdPolicy().thresholds(
            score_family=family,
            intervention_level=50,
        )
