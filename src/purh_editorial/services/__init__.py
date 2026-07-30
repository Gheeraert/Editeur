"""Réexportations publiques paresseuses des services éditoriaux.

L'import du paquet ne charge aucun service concret. Les symboles historiques
sont résolus à leur premier accès afin de conserver l'API publique sans faire
entrer prématurément les dépendances optionnelles (IA ou Word) en mémoire.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any


__all__ = [
    "AIEditorialService",
    "BibliographyNormalizer",
    "FootnoteNormalizer",
    "MetopesMapper",
    "OrthotypoService",
    "PivotCanonicalizer",
    "PivotValidationError",
    "PivotValidator",
    "StructurePreparationService",
    "WordReviewError",
    "WordReviewResult",
    "WordReviewService",
    "document_contains_tracked_changes",
    "WordReviewAnnotationResult",
    "WordReviewAnnotationService",
    "WordReviewComment",
    "WordWorkspaceService",
    "build_word_review_comments",
    "export_tei_for_production",
]


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "AIEditorialService": (
        "purh_editorial.services.ai_editorial_service",
        "AIEditorialService",
    ),
    "BibliographyNormalizer": (
        "purh_editorial.services.bibliography_normalizer",
        "BibliographyNormalizer",
    ),
    "FootnoteNormalizer": (
        "purh_editorial.services.footnote_normalizer",
        "FootnoteNormalizer",
    ),
    "MetopesMapper": (
        "purh_editorial.services.metopes_mapper",
        "MetopesMapper",
    ),
    "OrthotypoService": (
        "purh_editorial.services.orthotypo_service",
        "OrthotypoService",
    ),
    "PivotCanonicalizer": (
        "purh_editorial.services.pivot_canonicalizer",
        "PivotCanonicalizer",
    ),
    "PivotValidationError": (
        "purh_editorial.services.pivot_export_gate",
        "PivotValidationError",
    ),
    "PivotValidator": (
        "purh_editorial.services.pivot_validator",
        "PivotValidator",
    ),
    "StructurePreparationService": (
        "purh_editorial.services.structure_service",
        "StructurePreparationService",
    ),
    "WordReviewError": (
        "purh_editorial.services.word_review_service",
        "WordReviewError",
    ),
    "WordReviewResult": (
        "purh_editorial.services.word_review_service",
        "WordReviewResult",
    ),
    "WordReviewService": (
        "purh_editorial.services.word_review_service",
        "WordReviewService",
    ),
    "document_contains_tracked_changes": (
        "purh_editorial.services.word_review_service",
        "document_contains_tracked_changes",
    ),
    "WordReviewAnnotationResult": (
        "purh_editorial.services.word_review_annotation_service",
        "WordReviewAnnotationResult",
    ),
    "WordReviewAnnotationService": (
        "purh_editorial.services.word_review_annotation_service",
        "WordReviewAnnotationService",
    ),
    "WordReviewComment": (
        "purh_editorial.services.word_review_annotation_service",
        "WordReviewComment",
    ),
    "WordWorkspaceService": (
        "purh_editorial.services.word_workspace_service",
        "WordWorkspaceService",
    ),
    "build_word_review_comments": (
        "purh_editorial.services.word_review_annotation_service",
        "build_word_review_comments",
    ),
    "export_tei_for_production": (
        "purh_editorial.services.pivot_export_gate",
        "export_tei_for_production",
    ),
}


if TYPE_CHECKING:
    from purh_editorial.services.ai_editorial_service import AIEditorialService
    from purh_editorial.services.bibliography_normalizer import BibliographyNormalizer
    from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
    from purh_editorial.services.metopes_mapper import MetopesMapper
    from purh_editorial.services.orthotypo_service import OrthotypoService
    from purh_editorial.services.pivot_canonicalizer import PivotCanonicalizer
    from purh_editorial.services.pivot_export_gate import (
        PivotValidationError,
        export_tei_for_production,
    )
    from purh_editorial.services.pivot_validator import PivotValidator
    from purh_editorial.services.structure_service import StructurePreparationService
    from purh_editorial.services.word_review_annotation_service import (
        WordReviewAnnotationResult,
        WordReviewAnnotationService,
        WordReviewComment,
        build_word_review_comments,
    )
    from purh_editorial.services.word_review_service import (
        WordReviewError,
        WordReviewResult,
        WordReviewService,
        document_contains_tracked_changes,
    )
    from purh_editorial.services.word_workspace_service import WordWorkspaceService


def __getattr__(name: str) -> Any:
    """Résout et mémorise un réexport public demandé explicitement."""
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    module = importlib.import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose les réexportations pour l'introspection sans les charger."""
    return sorted(set(globals()) | set(__all__))
