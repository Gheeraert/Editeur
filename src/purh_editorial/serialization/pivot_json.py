from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from purh_editorial.model import (
    BibliographyItem,
    Block,
    Diagnostic,
    Document,
    Evidence,
    ComplexObjectOccurrence,
    ImageAsset,
    ImageOccurrence,
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
        "document": _document_to_data(document),
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


def _document_to_data(document: Document) -> dict[str, Any]:
    """Serialize media explicitly so binary data never reaches the generic serializer."""
    image_assets: dict[str, dict[str, Any]] = {}
    for asset_id, asset in document.image_assets.items():
        if asset_id != asset.asset_id:
            raise ValueError(
                f"Image asset key {asset_id!r} does not match asset_id {asset.asset_id!r}."
            )
        image_assets[asset_id] = _image_asset_to_data(asset)
    return {
        "document_id": document.document_id,
        "source_path": document.source_path,
        "source_format": document.source_format,
        "metadata": to_plain_data(document.metadata),
        "blocks": to_plain_data(document.blocks),
        "notes": to_plain_data(document.notes),
        "bibliography": to_plain_data(document.bibliography),
        "annotations": to_plain_data(document.annotations),
        "history": to_plain_data(document.history),
        "original_text": document.original_text,
        "image_assets": image_assets,
        "image_occurrences": to_plain_data(document.image_occurrences),
        "complex_objects": to_plain_data(document.complex_objects),
    }


def _image_asset_to_data(asset: ImageAsset) -> dict[str, Any]:
    return {
        "asset_id": asset.asset_id,
        "filename": asset.filename,
        "content_type": asset.content_type,
        "data": {
            "encoding": "base64",
            "value": base64.b64encode(asset.data).decode("ascii"),
        },
        "sha256": asset.sha256,
        "width_emu": asset.width_emu,
        "height_emu": asset.height_emu,
        "alt_text": asset.alt_text,
        "title": asset.title,
        "source_part": asset.source_part,
    }


def _document_from_data(data: dict[str, Any]) -> Document:
    if not isinstance(data, dict):
        raise ValueError("Pivot document must be a JSON object.")
    metadata = _metadata_from_data(data.get("metadata", {}))
    blocks = [_block_from_data(item) for item in data.get("blocks", []) if isinstance(item, dict)]
    notes = [_note_from_data(item) for item in data.get("notes", []) if isinstance(item, dict)]
    bibliography = [
        _bibliography_item_from_data(item)
        for item in data.get("bibliography", [])
        if isinstance(item, dict)
    ]
    image_assets = _image_assets_from_data(data.get("image_assets", {}))
    image_occurrences = _image_occurrences_from_data(
        data.get("image_occurrences", []), image_assets
    )
    complex_objects = _complex_objects_from_data(
        data.get("complex_objects", []), image_assets
    )
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
        image_assets=image_assets,
        image_occurrences=image_occurrences,
        complex_objects=complex_objects,
    )


def _image_assets_from_data(data: Any) -> dict[str, ImageAsset]:
    if not isinstance(data, dict):
        raise ValueError("Pivot image_assets must be an object.")

    assets: dict[str, ImageAsset] = {}
    for key, raw_asset in data.items():
        if not isinstance(key, str) or not isinstance(raw_asset, dict):
            raise ValueError("Each image_assets entry must be an object keyed by asset_id.")
        asset_id = _required_text(raw_asset, "asset_id", f"image asset {key!r}")
        if asset_id != key:
            raise ValueError(f"Image asset key {key!r} does not match asset_id {asset_id!r}.")
        assets[asset_id] = ImageAsset(
            asset_id=asset_id,
            filename=_required_text(raw_asset, "filename", f"image asset {asset_id!r}"),
            content_type=_required_text(raw_asset, "content_type", f"image asset {asset_id!r}"),
            data=_decode_image_data(raw_asset.get("data"), asset_id),
            sha256=_required_text(raw_asset, "sha256", f"image asset {asset_id!r}"),
            width_emu=_optional_int(raw_asset.get("width_emu"), "width_emu", asset_id),
            height_emu=_optional_int(raw_asset.get("height_emu"), "height_emu", asset_id),
            alt_text=_text_or_default(raw_asset.get("alt_text")),
            title=_text_or_default(raw_asset.get("title")),
            source_part=_text_or_default(raw_asset.get("source_part")),
        )
    return assets


def _decode_image_data(data: Any, asset_id: str) -> bytes:
    if not isinstance(data, dict):
        raise ValueError(f"Image asset {asset_id!r} data must be an encoded object.")
    if data.get("encoding") != "base64" or not isinstance(data.get("value"), str):
        raise ValueError(f"Image asset {asset_id!r} data must use base64 encoding.")
    try:
        return base64.b64decode(data["value"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Invalid base64 image data for asset {asset_id!r}.") from exc


def _image_occurrences_from_data(
    data: Any, image_assets: dict[str, ImageAsset]
) -> list[ImageOccurrence]:
    if not isinstance(data, list):
        raise ValueError("Pivot image_occurrences must be an array.")

    occurrences: list[ImageOccurrence] = []
    for index, raw_occurrence in enumerate(data):
        context = f"image occurrence at index {index}"
        if not isinstance(raw_occurrence, dict):
            raise ValueError(f"{context.capitalize()} must be an object.")
        asset_ref = _required_text(raw_occurrence, "asset_ref", context)
        if asset_ref not in image_assets:
            raise ValueError(f"{context.capitalize()} references missing asset {asset_ref!r}.")
        occurrences.append(
            ImageOccurrence(
                occurrence_id=_required_text(raw_occurrence, "occurrence_id", context),
                asset_ref=asset_ref,
                placement=_required_text(raw_occurrence, "placement", context),
                target_ref=_required_text(raw_occurrence, "target_ref", context),
                order=_required_int(raw_occurrence, "order", context),
                width_emu=_optional_int(raw_occurrence.get("width_emu"), "width_emu", context),
                height_emu=_optional_int(raw_occurrence.get("height_emu"), "height_emu", context),
                alt_text=_text_or_default(raw_occurrence.get("alt_text")),
                title=_text_or_default(raw_occurrence.get("title")),
                caption=_optional_text(raw_occurrence.get("caption")),
                external_link=_optional_text(raw_occurrence.get("external_link")),
                anchor_normalized_to_inline=_required_bool(
                    raw_occurrence, "anchor_normalized_to_inline", context
                ),
                original_xml=_optional_text(raw_occurrence.get("original_xml")),
                attributes=_required_mapping(raw_occurrence, "attributes", context),
            )
        )
    return occurrences


def _complex_objects_from_data(
    data: Any, image_assets: dict[str, ImageAsset]
) -> list[ComplexObjectOccurrence]:
    if not isinstance(data, list):
        raise ValueError("Pivot complex_objects must be an array.")

    objects: list[ComplexObjectOccurrence] = []
    for index, raw_object in enumerate(data):
        context = f"complex object at index {index}"
        if not isinstance(raw_object, dict):
            raise ValueError(f"{context.capitalize()} must be an object.")
        fallback_asset_ref = _optional_text(raw_object.get("fallback_asset_ref"))
        if fallback_asset_ref is not None and fallback_asset_ref not in image_assets:
            raise ValueError(
                f"{context.capitalize()} references missing fallback asset {fallback_asset_ref!r}."
            )
        objects.append(
            ComplexObjectOccurrence(
                occurrence_id=_required_text(raw_object, "occurrence_id", context),
                object_type=_required_text(raw_object, "object_type", context),
                target_ref=_required_text(raw_object, "target_ref", context),
                order=_required_int(raw_object, "order", context),
                placement=_required_text(raw_object, "placement", context),
                fallback_asset_ref=fallback_asset_ref,
                attributes=_required_mapping(raw_object, "attributes", context),
            )
        )
    return objects


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


def _required_text(data: dict[str, Any], field: str, context: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context.capitalize()} must define a non-empty {field!r}.")
    return value


def _text_or_default(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Media text fields must be strings.")
    return value


def _required_int(data: dict[str, Any], field: str, context: str) -> int:
    value = data.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{context.capitalize()} must define an integer {field!r}.")
    return value


def _optional_int(value: Any, field: str, context: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{context.capitalize()} field {field!r} must be an integer or null.")
    return value


def _required_bool(data: dict[str, Any], field: str, context: str) -> bool:
    value = data.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{context.capitalize()} must define a boolean {field!r}.")
    return value


def _required_mapping(data: dict[str, Any], field: str, context: str) -> dict[str, Any]:
    value = data.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"{context.capitalize()} field {field!r} must be an object.")
    return dict(value)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
