from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Evidence:
    excerpt: str = ""
    before: str = ""
    after: str = ""
    offset_start: int | None = None
    offset_end: int | None = None


@dataclass(slots=True)
class Diagnostic:
    diagnostic_id: str
    module: str
    severity: str
    category: str
    message: str
    target_ref: str
    evidence: Evidence = field(default_factory=Evidence)
    rule_id: str | None = None
    suggested_fix: str | None = None
    status: str = "open"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Suggestion:
    suggestion_id: str
    module: str
    target_ref: str
    message: str
    rationale: str
    proposed_text: str | None = None
    confidence: float | None = None
    caution_level: str = "high"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Transformation:
    transformation_id: str
    module: str
    target_ref: str
    operation: str
    before: str
    after: str
    rule_id: str | None = None
    applied: bool = False
    validated_by_human: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)
