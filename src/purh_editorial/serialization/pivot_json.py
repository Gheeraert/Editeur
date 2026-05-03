from __future__ import annotations

import json
from typing import Any

from purh_editorial.model import (
    BibliographyItem,
    Block,
    Diagnostic,
    Document,
    Evidence,
    InlineSpan,
    InlineStyle,
    Metadata,
    ModuleRun,
    Note,
    ProcessingReport,
    Suggestion,
    Transformation,
)
from purh_editorial.serialization.json_serializer import to_plain_data

SCHEMA_VERSION = "pivot-1.0"


def build_pivot_payload(
    document: Document,
    *,
    report: ProcessingReport | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "document": to_plain_data(document),
    }
    if report is not None:
        payload["report"] = to_plain_data(report)
    return payload


def pivot_to_json(
    document: Document,
    *,
    report: ProcessingReport | None = None,
    indent: int = 2,
) -> str:
    payload = build_pivot_payload(document, report=report)
    return json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True)


def parse_pivot_payload(value: str | dict[str, Any]) -> tuple[Document, ProcessingReport | None]:
    if isinstance(value, str):
        payload = json.loads(value)
    else:
        payload = value
    if not isinstance(payload, dict):
        raise ValueError("Pivot payload must be a JSON object.")

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema version: {payload.get('schema_version')!r}."
        )

    document = _document_from_data(payload.get("document", {}))
    report_raw = payload.get("report")
    report = _report_from_data(report_raw) if isinstance(report_raw, dict) else None
    return document, report


def _document_from_data(data: dict[str, Any]) -> Document:
    metadata = _metadata_from_data(data.get("metadata", {}))
    blocks = [_block_from_data(item) for item in data.get("blocks", []) if isinstance(item, dict)]
    notes = [_note_from_data(item) for item in data.get("notes", []) if isinstance(item, dict)]
    bibliography = [
        _bibliography_item_from_data(item)
        for item in data.get("bibliography", [])
        if isinstance(item, dict)
    ]
    return Document(
        document_id=str(data.get("document_id", "")),
        source_path=str(data.get("source_path", "")),
        source_format=str(data.get("source_format", "")),
        metadata=metadata,
        blocks=blocks,
        notes=notes,
        bibliography=bibliography,
        annotations=dict(data.get("annotations", {})),
        history=[str(item) for item in data.get("history", [])],
        original_text=str(data.get("original_text", "")),
    )


def _metadata_from_data(data: dict[str, Any]) -> Metadata:
    return Metadata(
        title=_optional_text(data.get("title")),
        subtitle=_optional_text(data.get("subtitle")),
        authors=[str(item) for item in data.get("authors", [])],
        language=_optional_text(data.get("language")),
        collection=_optional_text(data.get("collection")),
        publication_type=_optional_text(data.get("publication_type")),
        source_label=_optional_text(data.get("source_label")),
    )


def _block_from_data(data: dict[str, Any]) -> Block:
    inlines = [_inline_from_data(item) for item in data.get("inlines", []) if isinstance(item, dict)]
    children = [_block_from_data(item) for item in data.get("children", []) if isinstance(item, dict)]
    return Block(
        block_id=str(data.get("block_id", "")),
        block_type=str(data.get("block_type", "paragraph")),
        text=str(data.get("text", "")),
        inlines=inlines,
        note_refs=[str(item) for item in data.get("note_refs", [])],
        children=children,
        attributes=dict(data.get("attributes", {})),
        source_span=dict(data.get("source_span", {})),
    )


def _inline_from_data(data: dict[str, Any]) -> InlineSpan:
    style_raw = data.get("style", {})
    style = InlineStyle(
        bold=bool(style_raw.get("bold", False)),
        italic=bool(style_raw.get("italic", False)),
        small_caps=bool(style_raw.get("small_caps", False)),
        subscript=bool(style_raw.get("subscript", False)),
        superscript=bool(style_raw.get("superscript", False)),
    )
    return InlineSpan(
        text=str(data.get("text", "")),
        style=style,
        kind=str(data.get("kind", "text")),
        note_ref=_optional_text(data.get("note_ref")),
        attributes=dict(data.get("attributes", {})),
    )


def _note_from_data(data: dict[str, Any]) -> Note:
    inlines = [_inline_from_data(item) for item in data.get("inlines", []) if isinstance(item, dict)]
    return Note(
        note_id=str(data.get("note_id", "")),
        label=_optional_text(data.get("label")),
        text=str(data.get("text", "")),
        inlines=inlines,
        target_ref=_optional_text(data.get("target_ref")),
        attributes=dict(data.get("attributes", {})),
    )


def _bibliography_item_from_data(data: dict[str, Any]) -> BibliographyItem:
    return BibliographyItem(
        item_id=str(data.get("item_id", "")),
        raw_text=str(data.get("raw_text", "")),
        parsed_fields={str(k): str(v) for k, v in dict(data.get("parsed_fields", {})).items()},
        item_type=str(data.get("item_type", "unknown")),
        source_span=dict(data.get("source_span", {})),
    )


def _report_from_data(data: dict[str, Any]) -> ProcessingReport:
    module_runs = [_module_run_from_data(item) for item in data.get("module_runs", []) if isinstance(item, dict)]
    diagnostics = [_diagnostic_from_data(item) for item in data.get("diagnostics", []) if isinstance(item, dict)]
    suggestions = [_suggestion_from_data(item) for item in data.get("suggestions", []) if isinstance(item, dict)]
    transformations = [
        _transformation_from_data(item)
        for item in data.get("transformations", [])
        if isinstance(item, dict)
    ]
    return ProcessingReport(
        report_id=str(data.get("report_id", "")),
        document_id=str(data.get("document_id", "")),
        module_runs=module_runs,
        diagnostics=diagnostics,
        suggestions=suggestions,
        transformations=transformations,
        errors=[str(item) for item in data.get("errors", [])],
        warnings=[str(item) for item in data.get("warnings", [])],
        metadata=dict(data.get("metadata", {})),
    )


def _module_run_from_data(data: dict[str, Any]) -> ModuleRun:
    return ModuleRun(
        module_name=str(data.get("module_name", "")),
        version=str(data.get("version", "")),
        started_at=str(data.get("started_at", "")),
        finished_at=str(data.get("finished_at", "")),
        parameters=dict(data.get("parameters", {})),
        summary=dict(data.get("summary", {})),
        status=str(data.get("status", "success")),
    )


def _diagnostic_from_data(data: dict[str, Any]) -> Diagnostic:
    evidence_raw = data.get("evidence", {})
    evidence = Evidence(
        excerpt=str(evidence_raw.get("excerpt", "")),
        before=str(evidence_raw.get("before", "")),
        after=str(evidence_raw.get("after", "")),
        offset_start=evidence_raw.get("offset_start"),
        offset_end=evidence_raw.get("offset_end"),
    )
    return Diagnostic(
        diagnostic_id=str(data.get("diagnostic_id", "")),
        module=str(data.get("module", "")),
        severity=str(data.get("severity", "info")),
        category=str(data.get("category", "")),
        message=str(data.get("message", "")),
        target_ref=str(data.get("target_ref", "")),
        evidence=evidence,
        rule_id=_optional_text(data.get("rule_id")),
        suggested_fix=_optional_text(data.get("suggested_fix")),
        status=str(data.get("status", "open")),
        attributes=dict(data.get("attributes", {})),
    )


def _suggestion_from_data(data: dict[str, Any]) -> Suggestion:
    confidence = data.get("confidence")
    confidence_value = float(confidence) if isinstance(confidence, (int, float)) else None
    return Suggestion(
        suggestion_id=str(data.get("suggestion_id", "")),
        module=str(data.get("module", "")),
        target_ref=str(data.get("target_ref", "")),
        message=str(data.get("message", "")),
        rationale=str(data.get("rationale", "")),
        proposed_text=_optional_text(data.get("proposed_text")),
        confidence=confidence_value,
        caution_level=str(data.get("caution_level", "high")),
        attributes=dict(data.get("attributes", {})),
    )


def _transformation_from_data(data: dict[str, Any]) -> Transformation:
    return Transformation(
        transformation_id=str(data.get("transformation_id", "")),
        module=str(data.get("module", "")),
        target_ref=str(data.get("target_ref", "")),
        operation=str(data.get("operation", "")),
        before=str(data.get("before", "")),
        after=str(data.get("after", "")),
        rule_id=_optional_text(data.get("rule_id")),
        applied=bool(data.get("applied", False)),
        validated_by_human=bool(data.get("validated_by_human", False)),
        attributes=dict(data.get("attributes", {})),
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
