from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_ALL = [
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

EXPECTED_EXPORTS = {
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


def _run_fresh(code: str) -> dict[str, object]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_public_all_is_exact_and_ordered() -> None:
    services = importlib.import_module("purh_editorial.services")
    assert services.__all__ == EXPECTED_ALL


def test_importing_the_package_alone_loads_no_concrete_service() -> None:
    observed = _run_fresh(
        """
import json
import sys
import purh_editorial.services
prefix = "purh_editorial.services."
concrete_services = sorted(
    name for name in sys.modules
    if name.startswith(prefix) and name != "purh_editorial.services"
)
forbidden = sorted(
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or ".ui" in name
    or ".pipeline" in name
    or "structure_ai_arbitrator" in name
)
print(json.dumps({"services": concrete_services, "forbidden": forbidden}))
"""
    )
    assert observed == {"services": [], "forbidden": []}


def test_accessing_orthotypo_loads_only_its_required_branch() -> None:
    observed = _run_fresh(
        """
import json
import sys
from purh_editorial.services import OrthotypoService
print(json.dumps({
    "orthotypo": "purh_editorial.services.orthotypo_service" in sys.modules,
    "ai": "purh_editorial.services.ai_editorial_service" in sys.modules,
    "word": sorted(name for name in sys.modules if "word_" in name),
    "adapter": "purh_editorial.services.orthotypo_shadow_adapter" in sys.modules,
    "pipeline": sorted(
        name for name in sys.modules
        if name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    ),
    "ui": sorted(name for name in sys.modules if ".ui" in name),
}))
"""
    )
    assert observed == {
        "orthotypo": True,
        "ai": False,
        "word": [],
        "adapter": False,
        "pipeline": [],
        "ui": [],
    }


def test_accessing_bibliography_does_not_load_ai_or_word() -> None:
    observed = _run_fresh(
        """
import json
import sys
from purh_editorial.services import BibliographyNormalizer
print(json.dumps({
    "bibliography": "purh_editorial.services.bibliography_normalizer" in sys.modules,
    "ai": "purh_editorial.services.ai_editorial_service" in sys.modules,
    "word": sorted(name for name in sys.modules if "word_" in name),
    "adapter": "purh_editorial.services.orthotypo_shadow_adapter" in sys.modules,
    "pipeline": sorted(
        name for name in sys.modules
        if name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    ),
    "ui": sorted(name for name in sys.modules if ".ui" in name),
}))
"""
    )
    assert observed == {
        "bibliography": True,
        "ai": False,
        "word": [],
        "adapter": False,
        "pipeline": [],
        "ui": [],
    }


def test_first_access_caches_the_exact_origin_object() -> None:
    observed = _run_fresh(
        """
import json
import purh_editorial.services as services
before = "OrthotypoService" in vars(services)
first = services.OrthotypoService
second = services.OrthotypoService
from purh_editorial.services.orthotypo_service import OrthotypoService as origin
print(json.dumps({
    "before": before,
    "cached": "OrthotypoService" in vars(services),
    "stable": first is second,
    "origin": first is origin,
}))
"""
    )
    assert observed == {
        "before": False,
        "cached": True,
        "stable": True,
        "origin": True,
    }


@pytest.mark.parametrize("public_name", EXPECTED_ALL)
def test_every_public_export_has_its_historical_identity(
    public_name: str,
) -> None:
    services = importlib.import_module("purh_editorial.services")
    module_name, attribute_name = EXPECTED_EXPORTS[public_name]
    origin_module = importlib.import_module(module_name)
    assert getattr(services, public_name) is getattr(origin_module, attribute_name)
    assert public_name in vars(services)


def test_unknown_attribute_raises_an_informative_attribute_error() -> None:
    services = importlib.import_module("purh_editorial.services")
    with pytest.raises(AttributeError) as error:
        services.UnknownService
    assert "purh_editorial.services" in str(error.value)
    assert "UnknownService" in str(error.value)


def test_dir_lists_all_public_exports_once_without_loading_them() -> None:
    observed = _run_fresh(
        """
import json
import purh_editorial.services as services
names = dir(services)
print(json.dumps({
    "includes_all": set(services.__all__) <= set(names),
    "unique": len(names) == len(set(names)),
    "cached": [name for name in services.__all__ if name in vars(services)],
}))
"""
    )
    assert observed == {"includes_all": True, "unique": True, "cached": []}


def test_historical_public_imports_continue_to_work() -> None:
    observed = _run_fresh(
        """
import json
from purh_editorial.services import (
    OrthotypoService,
    PivotValidationError,
    WordReviewService,
    export_tei_for_production,
)
print(json.dumps({
    "orthotypo": OrthotypoService.__name__,
    "pivot_error": PivotValidationError.__name__,
    "word_review": WordReviewService.__name__,
    "export": export_tei_for_production.__name__,
}))
"""
    )
    assert observed == {
        "orthotypo": "OrthotypoService",
        "pivot_error": "PivotValidationError",
        "word_review": "WordReviewService",
        "export": "export_tei_for_production",
    }


def test_import_star_exposes_exactly_the_historical_public_names() -> None:
    observed = _run_fresh(
        """
import json
namespace = {}
exec("from purh_editorial.services import *", namespace)
print(json.dumps(sorted(name for name in namespace if name != "__builtins__")))
"""
    )
    assert observed == sorted(EXPECTED_ALL)
