from __future__ import annotations

from purh_editorial.rules.model import ThresholdPair


class InvalidInterventionLevelError(ValueError):
    """Le niveau natif d'intervention n'appartient pas à l'intervalle 0..100."""


class UncalibratedScoreFamilyError(ValueError):
    """La famille de score ne possède pas encore de calibration native."""


_ANCHORS: dict[str, tuple[tuple[int, ThresholdPair], ...]] = {
    "heading": (
        (0, ThresholdPair(review=0.70, apply=0.90)),
        (50, ThresholdPair(review=0.60, apply=0.85)),
        (100, ThresholdPair(review=0.50, apply=0.75)),
    ),
    "poetry": (
        (0, ThresholdPair(review=0.60, apply=0.82)),
        (50, ThresholdPair(review=0.55, apply=0.78)),
        (100, ThresholdPair(review=0.48, apply=0.72)),
    ),
}


class CanonicalThresholdPolicy:
    """Traduit le niveau natif en seuils propres à une famille calibrée."""

    def thresholds(
        self,
        *,
        score_family: str,
        intervention_level: int,
    ) -> ThresholdPair:
        if isinstance(intervention_level, bool) or not isinstance(
            intervention_level, int
        ):
            raise InvalidInterventionLevelError(
                "intervention_level must be an integer between 0 and 100"
            )
        if not 0 <= intervention_level <= 100:
            raise InvalidInterventionLevelError(
                "intervention_level must be between 0 and 100"
            )

        anchors = _ANCHORS.get(score_family)
        if anchors is None:
            raise UncalibratedScoreFamilyError(
                f"uncalibrated score family: {score_family!r}"
            )

        for level, thresholds in anchors:
            if intervention_level == level:
                return thresholds

        lower, upper = (
            (anchors[0], anchors[1])
            if intervention_level < 50
            else (anchors[1], anchors[2])
        )
        lower_level, lower_thresholds = lower
        upper_level, upper_thresholds = upper
        ratio = (intervention_level - lower_level) / (upper_level - lower_level)
        return ThresholdPair(
            review=lower_thresholds.review
            + ratio * (upper_thresholds.review - lower_thresholds.review),
            apply=lower_thresholds.apply
            + ratio * (upper_thresholds.apply - lower_thresholds.apply),
        )
