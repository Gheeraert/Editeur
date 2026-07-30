"""Diagnostic privé, XML-first, des occurrences natives de ``purh.siecles``.

Le batch shadow sert seulement à sélectionner les actions natives déjà produites.
La qualification lit directement les runs OOXML : aucune conclusion n'est tirée
du seul texte extrait.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence
import xml.etree.ElementTree as ET
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from purh_editorial.config.private_corpus import (  # noqa: E402
    ENV_VAR,
    resolve_private_corpus_dir,
)
from purh_editorial.io.importer_registry import ImporterRegistry  # noqa: E402
from purh_editorial.model import Document, InlineSpan  # noqa: E402
from purh_editorial.rules.orthotypography.century_rule import (  # noqa: E402
    RULE_ID,
    _VALID_CENTURIES,
)
from purh_editorial.services.orthotypo_shadow_batch import (  # noqa: E402
    OrthotypoShadowBatchRunner,
)


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_W = "{" + NS["w"] + "}"
_ROMAN_SHORT_RE = re.compile(r"([ivxlcdm]{1,8})e")
_CENTURY_LEXICAL_RE = re.compile(r"([IVXLCDMivxlcdm]{1,8})([eè][rm]?[eé]?)")
_FALSE_VALUES = {"0", "false", "off", "no"}
_REVISION_TAGS = {
    "ins": "insertion",
    "del": "deletion",
    "moveFrom": "move_from",
    "moveTo": "move_to",
}


class CenturyFormattingInputError(ValueError):
    """Les entrées privées du diagnostic ne respectent pas son contrat."""


@dataclass(frozen=True, slots=True)
class _RunSegment:
    text: str
    start: int
    end: int
    properties: dict[str, bool | None | str]
    revision_kind: str | None


@dataclass(frozen=True, slots=True)
class _XmlTarget:
    target_ref: str
    text: str
    runs: tuple[_RunSegment, ...]


@dataclass(frozen=True, slots=True)
class _StyleDefinition:
    style_id: str
    based_on: str | None
    name: str
    properties: dict[str, bool | None]


class _StyleResolver:
    def __init__(self, styles_xml: bytes | None) -> None:
        self._styles: dict[str, _StyleDefinition] = {}
        self._defaults: dict[str, bool | None] = _empty_properties()
        if styles_xml is not None:
            self._load(styles_xml)

    def _load(self, styles_xml: bytes) -> None:
        root = ET.fromstring(styles_xml)
        default_rpr = root.find("./w:docDefaults/w:rPrDefault/w:rPr", NS)
        if default_rpr is not None:
            self._defaults = _properties_from_rpr(default_rpr)
        for style in root.findall("./w:style", NS):
            style_id = style.get(_W + "styleId")
            if not style_id:
                continue
            based_on = style.find("./w:basedOn", NS)
            name = style.find("./w:name", NS)
            rpr = style.find("./w:rPr", NS)
            self._styles[style_id] = _StyleDefinition(
                style_id=style_id,
                based_on=(based_on.get(_W + "val") if based_on is not None else None),
                name=(name.get(_W + "val", "") if name is not None else ""),
                properties=(
                    _properties_from_rpr(rpr) if rpr is not None else _empty_properties()
                ),
            )

    def resolve_run(self, run: ET.Element, paragraph: ET.Element) -> dict[str, bool | None | str]:
        run_rpr = run.find("./w:rPr", NS)
        paragraph_rpr = paragraph.find("./w:pPr/w:rPr", NS)
        paragraph_style = paragraph.find("./w:pPr/w:pStyle", NS)
        run_style = run_rpr.find("./w:rStyle", NS) if run_rpr is not None else None
        paragraph_style_id = (
            paragraph_style.get(_W + "val") if paragraph_style is not None else None
        )
        run_style_id = run_style.get(_W + "val") if run_style is not None else None
        properties = dict(self._defaults)
        _overlay(properties, self._resolve_style(paragraph_style_id))
        _overlay(properties, _properties_from_rpr(paragraph_rpr))
        _overlay(properties, self._resolve_style(run_style_id))
        _overlay(properties, _properties_from_rpr(run_rpr))
        selected_style = run_style_id or paragraph_style_id
        properties["style_name"] = (
            self._styles[selected_style].name
            if selected_style in self._styles
            else ""
        )
        return properties

    def _resolve_style(
        self, style_id: str | None, seen: set[str] | None = None
    ) -> dict[str, bool | None]:
        if not style_id or style_id not in self._styles:
            return _empty_properties()
        seen = set() if seen is None else seen
        if style_id in seen:
            return _empty_properties()
        seen.add(style_id)
        style = self._styles[style_id]
        properties = self._resolve_style(style.based_on, seen)
        _overlay(properties, style.properties)
        return properties


def _empty_properties() -> dict[str, bool | None]:
    return {
        "small_caps": None,
        "caps": None,
        "superscript": None,
        "subscript": None,
        "bold": None,
        "italic": None,
    }


def _overlay(
    destination: dict[str, bool | None], source: dict[str, bool | None]
) -> None:
    for name, value in source.items():
        if value is not None:
            destination[name] = value


def _bool_property(rpr: ET.Element | None, tag: str) -> bool | None:
    if rpr is None:
        return None
    node = rpr.find("./w:" + tag, NS)
    if node is None:
        return None
    return node.get(_W + "val", "1").lower() not in _FALSE_VALUES


def _properties_from_rpr(rpr: ET.Element | None) -> dict[str, bool | None]:
    properties = _empty_properties()
    properties["small_caps"] = _bool_property(rpr, "smallCaps")
    properties["caps"] = _bool_property(rpr, "caps")
    properties["bold"] = _bool_property(rpr, "b")
    properties["italic"] = _bool_property(rpr, "i")
    if rpr is not None:
        vertical = rpr.find("./w:vertAlign", NS)
        if vertical is not None:
            value = vertical.get(_W + "val", "")
            properties["superscript"] = value == "superscript"
            properties["subscript"] = value == "subscript"
    return properties


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _run_text(
    run: ET.Element,
    *,
    revision_kind: str | None,
    note_labels: dict[str, str],
) -> str:
    text_tags = {"delText"} if revision_kind == "deletion" else {"t"}
    pieces: list[str] = []
    for child in list(run):
        local_name = _local_name(child)
        if local_name in text_tags:
            pieces.append(child.text or "")
        elif revision_kind is None and local_name == "tab":
            pieces.append("\t")
        elif revision_kind is None and local_name in {"br", "cr"}:
            pieces.append("\n")
        elif revision_kind is None and local_name in {"footnoteReference", "endnoteReference"}:
            raw_id = child.get(_W + "id")
            if raw_id:
                pieces.append(f"[{note_labels.get(f'ftn{raw_id}', raw_id)}]")
    return "".join(pieces)


def _paragraph_target(
    *,
    target_ref: str,
    paragraph: ET.Element,
    resolver: _StyleResolver,
    note_labels: dict[str, str],
    include_revisions: bool = False,
) -> _XmlTarget:
    runs: list[_RunSegment] = []
    position = 0

    def visit(element: ET.Element, revision_kind: str | None = None) -> None:
        nonlocal position
        local_name = _local_name(element)
        if local_name in _REVISION_TAGS:
            for child in list(element):
                visit(child, _REVISION_TAGS[local_name])
            return
        if local_name == "r":
            if revision_kind is not None and not include_revisions:
                return
            text = _run_text(
                element,
                revision_kind=revision_kind,
                note_labels=note_labels,
            )
            if not text:
                return
            start = position
            position += len(text)
            runs.append(
                _RunSegment(
                    text=text,
                    start=start,
                    end=position,
                    properties=resolver.resolve_run(element, paragraph),
                    revision_kind=revision_kind,
                )
            )
            return
        for child in list(element):
            visit(child, revision_kind)

    # Reproduit le parcours de DocxImporter._paragraph_inlines : seuls les runs
    # enfants directs sont intégrés au texte pivot. Les conteneurs (hyperliens,
    # révisions…) restent donc non alignables plutôt que d'être interprétés.
    for child in list(paragraph):
        if _local_name(child) == "r":
            visit(child)
    return _XmlTarget(
        target_ref=target_ref,
        text="".join(run.text for run in runs),
        runs=tuple(runs),
    )


def _read_docx_targets(path: Path) -> dict[str, _XmlTarget]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
        styles_xml = archive.read("word/styles.xml") if "word/styles.xml" in archive.namelist() else None
        footnotes_xml = archive.read("word/footnotes.xml") if "word/footnotes.xml" in archive.namelist() else None
    resolver = _StyleResolver(styles_xml)
    document = ET.fromstring(document_xml)
    targets: dict[str, _XmlTarget] = {}
    note_labels: dict[str, str] = {}
    if footnotes_xml is not None:
        footnotes_root = ET.fromstring(footnotes_xml)
        for footnote in footnotes_root.findall("./w:footnote", NS):
            raw_id = footnote.get(_W + "id", "")
            note_labels[f"ftn{raw_id}"] = raw_id
    # DocxImporter attribue les identifiants de blocs à partir de b1.
    block_index = 1
    body = document.find("./w:body", NS)
    if body is not None:
        for child in list(body):
            local_name = _local_name(child)
            if local_name == "tbl":
                block_index += 1
            elif local_name == "p":
                targets[f"b{block_index}"] = _paragraph_target(
                    target_ref=f"b{block_index}",
                    paragraph=child,
                    resolver=resolver,
                    note_labels=note_labels,
                )
                block_index += 1
    if footnotes_xml is not None:
        footnotes = ET.fromstring(footnotes_xml)
        for footnote in footnotes.findall("./w:footnote", NS):
            footnote_type = footnote.get(_W + "type", "")
            if footnote_type in {"separator", "continuationSeparator"}:
                continue
            raw_id = footnote.get(_W + "id", "")
            target_ref = f"ftn{raw_id}"
            parts = [
                _paragraph_target(
                    target_ref=target_ref,
                    paragraph=paragraph,
                    resolver=resolver,
                    note_labels=note_labels,
                )
                for paragraph in footnote.findall("./w:p", NS)
            ]
            text = "\n".join(part.text for part in parts)
            runs: list[_RunSegment] = []
            offset = 0
            for index, part in enumerate(parts):
                for run in part.runs:
                    runs.append(
                        _RunSegment(
                            text=run.text,
                            start=run.start + offset,
                            end=run.end + offset,
                            properties=run.properties,
                            revision_kind=run.revision_kind,
                        )
                    )
                offset += len(part.text) + (1 if index < len(parts) - 1 else 0)
            targets[target_ref] = _XmlTarget(target_ref, text, tuple(runs))
    return targets


def _find_document_target(document: Document, target_ref: str) -> tuple[str, list[InlineSpan]] | None:
    for block in document.blocks:
        if block.block_id == target_ref:
            return block.text, block.inlines
    for note in document.notes:
        if note.note_id == target_ref:
            return note.text, note.inlines
    return None


def four_j_bis_would_filter(*, action: Any, document: Document, target_ref: str, target_text: str) -> bool:
    """Reproduction isolée de la condition historique du commit ``cbdfa20``."""
    if not isinstance(action.before, str):
        return False
    match = _ROMAN_SHORT_RE.fullmatch(action.before)
    if match is None or match.group(1) not in _VALID_CENTURIES:
        return False
    start, end = action.offset_start, action.offset_end
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end < start
        or target_text[start:end] != action.before
    ):
        return False
    source = _find_document_target(document, target_ref)
    if source is None:
        return False
    _source_text, inlines = source
    if not inlines or "".join(span.text for span in inlines) != target_text:
        return False
    character_styles = tuple(
        (span.kind, span.style.small_caps, span.style.superscript)
        for span in inlines
        for _character in span.text
    )
    fragment = character_styles[start:end]
    if len(fragment) != len(action.before):
        return False
    roman, suffix = fragment[:-1], fragment[-1]
    return (
        all(kind == "text" and small_caps for kind, small_caps, _sup in roman)
        and suffix[0] == "text"
        and suffix[2]
    )


def _project_segments(
    target: _XmlTarget, start: int, end: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    segments: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []
    for run in target.runs:
        boundaries.append(
            {
                "start": run.start,
                "end": run.end,
                "revision_kind": run.revision_kind,
            }
        )
        overlap_start, overlap_end = max(start, run.start), min(end, run.end)
        if overlap_start >= overlap_end:
            continue
        relative_start = overlap_start - start
        relative_end = overlap_end - start
        properties = run.properties
        segments.append(
            {
                "text": run.text[overlap_start - run.start : overlap_end - run.start],
                "relative_start": relative_start,
                "relative_end": relative_end,
                "small_caps": properties["small_caps"],
                "caps": properties["caps"],
                "superscript": properties["superscript"],
                "subscript": properties["subscript"],
                "bold": properties["bold"],
                "italic": properties["italic"],
                "style_name": properties["style_name"],
                "revision_kind": run.revision_kind,
            }
        )
    return segments, boundaries


def classify_century_occurrence(
    *,
    text_before: str,
    target_text: str,
    offset_start: int | None,
    offset_end: int | None,
    segments: Sequence[dict[str, Any]],
    mapping_reason: str | None = None,
) -> tuple[str, str, tuple[str, ...]]:
    """Retourne classe, action informative et raisons déterministes."""
    reasons: list[str] = []
    if mapping_reason is not None:
        return "indeterminate", "review", (mapping_reason,)
    if (
        isinstance(offset_start, bool)
        or isinstance(offset_end, bool)
        or not isinstance(offset_start, int)
        or not isinstance(offset_end, int)
        or offset_start < 0
        or offset_end < offset_start
        or target_text[offset_start:offset_end] != text_before
    ):
        return "indeterminate", "review", ("offset_mapping_unverified",)
    lexical = _CENTURY_LEXICAL_RE.fullmatch(text_before)
    if lexical is None or lexical.group(1).lower() not in _VALID_CENTURIES:
        return "indeterminate", "review", ("lexical_form_unverified",)
    if any(segment["revision_kind"] is not None for segment in segments):
        return "indeterminate", "review", ("revision_state_indeterminate",)
    if not segments or "".join(segment["text"] for segment in segments) != text_before:
        return "indeterminate", "review", ("character_coverage_incomplete",)
    suffix = lexical.group(2)
    if suffix != "e":
        return (
            "noncompliant_textual_form",
            "transformation_and_styling",
            ("long_suffix_recognized_by_century_rule",),
        )
    roman = lexical.group(1)
    if roman != roman.lower():
        return "indeterminate", "review", ("short_form_not_internal_lowercase",)
    characters = [
        (character, segment)
        for segment in segments
        for character in segment["text"]
    ]
    roman_characters, suffix_character = characters[:-1], characters[-1]
    required = [
        segment["small_caps"] for _character, segment in roman_characters
    ] + [suffix_character[1]["superscript"]]
    if any(value is None for value in required):
        return "indeterminate", "review", ("required_style_unset_or_inherited",)
    if any(segment["caps"] is True for _character, segment in roman_characters):
        reasons.append("caps_contradicts_small_caps")
    if suffix_character[1]["subscript"] is True:
        reasons.append("subscript_contradicts_superscript")
    if not all(required):
        reasons.append("required_small_caps_or_superscript_missing")
    if reasons:
        return "noncompliant_missing_or_wrong_styling", "styling", tuple(reasons)
    return "compliant_purh_styled", "none", ("small_caps_and_superscript_verified",)


def _excerpt(text: str, start: int | None, end: int | None) -> str:
    if not isinstance(start, int) or not isinstance(end, int):
        return ""
    return text[max(0, start - 40) : min(len(text), end + 40)].replace("\n", " ")


def _analyze_document(
    *,
    path: Path,
    document_kind: str,
    document_label: str,
) -> list[dict[str, Any]]:
    document = ImporterRegistry().load_document(path)
    xml_targets = _read_docx_targets(path)
    batch = OrthotypoShadowBatchRunner().run(document)
    rule_result = batch.for_rule(RULE_ID)
    records: list[dict[str, Any]] = []
    for sequence, (decision, comparison, target) in enumerate(
        zip(rule_result.native_decisions, rule_result.comparisons, rule_result.targets)
    ):
        for action_index, action in enumerate(decision.proposed_actions):
            xml_target = xml_targets.get(target.target_ref)
            mapping_reason = None
            if xml_target is None:
                mapping_reason = "xml_target_not_found"
                segments, boundaries = [], []
            elif xml_target.text != target.text:
                mapping_reason = "xml_text_does_not_match_imported_target"
                segments, boundaries = [], []
            else:
                segments, boundaries = _project_segments(
                    xml_target, action.offset_start, action.offset_end
                )
            classification, expected_action, reasons = classify_century_occurrence(
                text_before=action.before,
                target_text=target.text,
                offset_start=action.offset_start,
                offset_end=action.offset_end,
                segments=segments,
                mapping_reason=mapping_reason,
            )
            records.append(
                {
                    "document_label": document_label,
                    "document_kind": document_kind,
                    "document_filename": path.name,
                    "target_ref": target.target_ref,
                    "sequence": sequence,
                    "action_index": action_index,
                    "text_before": action.before,
                    "text_after_native": action.after,
                    "offset_start": action.offset_start,
                    "offset_end": action.offset_end,
                    "context_excerpt": _excerpt(target.text, action.offset_start, action.offset_end),
                    "run_count": len(boundaries),
                    "run_boundaries": boundaries,
                    "character_segments": segments,
                    "legacy_action_count": len(comparison.legacy_observation.observed_actions),
                    "native_action_count": len(decision.proposed_actions),
                    "native_decision": decision.outcome.value,
                    "protected": target.protection.protected,
                    "classification": classification,
                    "classification_reasons": list(reasons),
                    "expected_editorial_action": expected_action,
                    "four_j_bis_would_filter": four_j_bis_would_filter(
                        action=action,
                        document=document,
                        target_ref=target.target_ref,
                        target_text=target.text,
                    ),
                }
            )
    return records


def _summary(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    classifications = Counter(record["classification"] for record in records)
    actions = Counter(record["expected_editorial_action"] for record in records)
    per_kind: dict[str, dict[str, dict[str, int]]] = {}
    for kind in ("author", "edited_reference"):
        subset = [record for record in records if record["document_kind"] == kind]
        per_kind[kind] = {
            "classifications": dict(Counter(item["classification"] for item in subset)),
            "expected_editorial_actions": dict(Counter(item["expected_editorial_action"] for item in subset)),
        }
    filtered = [record for record in records if record["four_j_bis_would_filter"]]
    compliant = [record for record in records if record["classification"] == "compliant_purh_styled"]
    false_positives = [record for record in filtered if record not in compliant]
    false_negatives = [record for record in compliant if record not in filtered]
    exact = [record for record in filtered if record in compliant]
    return {
        "classification_counts": dict(classifications),
        "expected_editorial_action_counts": dict(actions),
        "per_document_kind": per_kind,
        "four_j_bis": {
            "would_filter_count": len(filtered),
            "four_j_bis_false_positive_count": len(false_positives),
            "four_j_bis_false_negative_count": len(false_negatives),
            "four_j_bis_exact_match_count": len(exact),
            "all_filtered_are_compliant": not false_positives,
            "all_compliant_are_filtered": not false_negatives,
            "filtered_noncompliant_textual_form": any(record["classification"] == "noncompliant_textual_form" for record in filtered),
            "filtered_noncompliant_missing_or_wrong_styling": any(record["classification"] == "noncompliant_missing_or_wrong_styling" for record in filtered),
            "filtered_indeterminate": any(record["classification"] == "indeterminate" for record in filtered),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Analyse privée du formatage des siècles",
        "",
        "La classification est déterminée depuis les runs OOXML, non depuis le seul texte extrait.",
        "",
        "## Compteurs par corpus",
        "",
    ]
    for kind, values in summary["per_document_kind"].items():
        lines.extend([f"### {kind}", ""])
        for classification, count in sorted(values["classifications"].items()):
            lines.append(f"- `{classification}` : {count}")
        for action, count in sorted(values["expected_editorial_actions"].items()):
            lines.append(f"- action attendue `{action}` : {count}")
        lines.append("")
    lines.extend(["## Matrice 4J-bis", ""])
    for key, value in summary["four_j_bis"].items():
        if key not in {"false_positives", "false_negatives"}:
            lines.append(f"- `{key}` : `{value}`")
    for title, records in (
        ("Faux positifs", summary["four_j_bis"]["false_positives"]),
        ("Faux négatifs", summary["four_j_bis"]["false_negatives"]),
        ("Occurrences indeterminate", [r for r in report["occurrences"] if r["classification"] == "indeterminate"]),
    ):
        lines.extend(["", f"## {title}", ""])
        if not records:
            lines.append("Aucune occurrence.")
        else:
            for record in records:
                lines.append(
                    "- `{label}` · `{target}` · offsets {start}-{end} · `{classification}` · {reasons}".format(
                        label=record["document_label"], target=record["target_ref"],
                        start=record["offset_start"], end=record["offset_end"],
                        classification=record["classification"],
                        reasons=", ".join(record["classification_reasons"]),
                    )
                )
    lines.extend(["", "## Exemples représentatifs", ""])
    for classification in (
        "compliant_purh_styled",
        "noncompliant_textual_form",
        "noncompliant_missing_or_wrong_styling",
        "indeterminate",
    ):
        examples = [
            record for record in report["occurrences"]
            if record["classification"] == classification
        ][:3]
        lines.append(f"### {classification}")
        if not examples:
            lines.append("Aucune occurrence.")
        else:
            for record in examples:
                lines.append(
                    "- `{label}` · `{target}` · forme `{before}` · {reasons}".format(
                        label=record["document_label"],
                        target=record["target_ref"],
                        before=record["text_before"],
                        reasons=", ".join(record["classification_reasons"]),
                    )
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def evaluate_corpus(*, raw_docx: Path, reference_dir: Path, output_dir: Path) -> dict[str, Any]:
    private_root = resolve_private_corpus_dir()
    _validate_inputs(raw_docx, reference_dir, output_dir, private_root)
    reference_paths = sorted(reference_dir.rglob("*.docx"))
    records = _analyze_document(path=raw_docx, document_kind="author", document_label="author-001")
    for index, path in enumerate(reference_paths, start=1):
        records.extend(_analyze_document(path=path, document_kind="edited_reference", document_label=f"reference-{index:03d}"))
    report = {"schema_version": 1, "occurrences": records, "summary": _summary(records)}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "century_formatting_analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "century_formatting_analysis.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _validate_inputs(raw_docx: Path, reference_dir: Path, output_dir: Path, private_root: Path) -> None:
    if not raw_docx.is_file() or raw_docx.suffix.lower() != ".docx":
        raise CenturyFormattingInputError("--raw-docx doit désigner un DOCX existant")
    if not reference_dir.is_dir() or not list(reference_dir.rglob("*.docx")):
        raise CenturyFormattingInputError("--reference-dir doit contenir au moins un DOCX")
    if not _is_within(raw_docx, private_root) or not _is_within(reference_dir, private_root) or not _is_within(output_dir, private_root):
        raise CenturyFormattingInputError("les entrées et la sortie doivent rester dans le corpus privé configuré")
    if _is_within(output_dir, REPOSITORY_ROOT):
        raise CenturyFormattingInputError("--output-dir ne doit pas être sous le dépôt")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-docx", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = evaluate_corpus(raw_docx=args.raw_docx, reference_dir=args.reference_dir, output_dir=args.output_dir)
    except CenturyFormattingInputError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # Diagnostic local : aucun contenu privé dans stderr.
        print(f"Erreur technique : {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(report["summary"]["classification_counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
