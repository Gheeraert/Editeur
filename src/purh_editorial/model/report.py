from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from purh_editorial.model.annotations import Diagnostic, Suggestion, Transformation


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ModuleRun:
    module_name: str
    version: str
    started_at: str
    finished_at: str
    parameters: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    status: str = "success"


@dataclass(slots=True)
class ProcessingReport:
    report_id: str
    document_id: str
    module_runs: list[ModuleRun] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    transformations: list[Transformation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_module_run(self, module_run: ModuleRun) -> None:
        self.module_runs.append(module_run)

    def merge(self, other: "ProcessingReport") -> None:
        self.module_runs.extend(other.module_runs)
        self.diagnostics.extend(other.diagnostics)
        self.suggestions.extend(other.suggestions)
        self.transformations.extend(other.transformations)
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)
