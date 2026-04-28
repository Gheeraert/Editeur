from __future__ import annotations

from dataclasses import dataclass, field

from purh_editorial.model.document import Document
from purh_editorial.model.report import ProcessingReport


@dataclass(slots=True)
class PipelineResult:
    source_document: Document
    styled_document: Document
    report: ProcessingReport
    pivot_payload: dict = field(default_factory=dict)
