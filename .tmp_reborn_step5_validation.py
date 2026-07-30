from __future__ import annotations

import csv
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile

from purh_editorial.corrector import correct_docx
from purh_editorial.corrector.runner import RULE_IDS

PRIVATE_ROOT = Path(os.environ["PURH_PRIVATE_CORPUS_DIR"]).resolve()
REPORT_ROOT = (PRIVATE_ROOT / "private_reports" / "reborn_step5").resolve()
EXPECTED_REPORT_ROOT = Path(
    r"F:\Mon Drive\Editeur-private\private_reports\reborn_step5"
).resolve()

SOURCE_ROOTS = {
    "io_samples": PRIVATE_ROOT / "sources" / "io_samples",
    "output_samples": PRIVATE_ROOT / "sources" / "output_samples",
}

WD_YELLOW = 7
WD_TURQUOISE = 3
STORY_TYPES = range(1, 12)
WD_UNDEFINED = 9999999
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def qn(local_name: str) -> str:
    return f"{{{WORD_NS}}}{local_name}"

DIAGNOSTIC_RULE_IDS = {
    "R-TI-001",
    "R-AN-002",
    "R-AN-003",
    "purh.guillemets.droits",
    "purh.tiret.double",
    "R-GQ-004",
    "R-AN-004",
    "R-AN-005",
}
PIPELINE_RULE_IDS = {
    "structure.frontmatter.circuit_breaker",
    "structure.bibliography.section.start",
    "structure.bibliography.section.end",
    "structure.bibliography.section",
}
AUTOMATIC_RULE_IDS = set(RULE_IDS) - DIAGNOSTIC_RULE_IDS - PIPELINE_RULE_IDS
STYLE_TARGET_RE = re.compile(
    r"(?:\b(?:[ivx]{1,5})(?:er|e|ème|eme)\s+siècles?\b|"
    r"\b[Nn](?:o|°|º)[ \t\u00a0\u202f]*\d)",
    re.IGNORECASE,
)
STRUCTURE_RULE_IDS = {
    rule_id
    for rule_id in RULE_IDS
    if rule_id.startswith("structure.")
    or rule_id in {"R-STRUCT-HEADING-001", "R-CI-POETRY-001"}
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_docx(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.docx")
        if not path.name.startswith("~$")
        and "private_reports" not in path.parts
        and "reborn" not in path.name.lower()
    )


def word_application() -> Any:
    from win32com.client import DispatchEx

    word = DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    return word


def visible_texts(path: Path) -> dict[str, str]:
    word = word_application()
    document = None
    try:
        document = word.Documents.Open(
            FileName=str(path),
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )
        result = {"main": document.StoryRanges(1).Text}
        for index in range(1, document.Footnotes.Count + 1):
            result[f"footnote:{index}"] = document.Footnotes(index).Range.Text
        return result
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def iter_story_ranges(document: Any):
    for story_type in STORY_TYPES:
        try:
            story = document.StoryRanges(story_type)
        except Exception:
            continue
        linked_index = 0
        while story is not None:
            current = story.Duplicate
            yield f"{story_type}:{linked_index}", story_type, current
            try:
                story = story.NextStoryRange
            except Exception:
                story = None
            linked_index += 1


def ooxml_run_text(run: Any) -> str:
    chunks: list[str] = []
    for element in run.iter():
        if element.tag in (qn("t"), qn("instrText"), qn("delText")):
            chunks.append(element.text or "")
        elif element.tag == qn("tab"):
            chunks.append("\t")
        elif element.tag in (qn("br"), qn("cr")):
            chunks.append("\n")
        elif element.tag == qn("noBreakHyphen"):
            chunks.append("\u2011")
        elif element.tag == qn("softHyphen"):
            chunks.append("\u00ad")
    return "".join(chunks)


def ooxml_stories(path: Path) -> dict[str, Any]:
    stories: dict[str, Any] = {}
    with ZipFile(path) as archive:
        part_names = sorted(
            name
            for name in archive.namelist()
            if name == "word/document.xml"
            or name == "word/footnotes.xml"
            or name == "word/endnotes.xml"
            or name == "word/comments.xml"
            or (
                name.startswith("word/header")
                and name.endswith(".xml")
            )
            or (
                name.startswith("word/footer")
                and name.endswith(".xml")
            )
        )
        for part_name in part_names:
            root = ElementTree.fromstring(archive.read(part_name))
            text_chunks: list[str] = []
            paragraphs: list[dict[str, Any]] = []
            highlights: list[dict[str, Any]] = []
            smallcaps: list[tuple[int, int]] = []
            superscript: list[tuple[int, int]] = []
            offset = 0
            paragraph_index = 0
            for paragraph in root.iter(qn("p")):
                paragraph_index += 1
                paragraph_start = offset
                paragraph_style = ""
                paragraph_properties = paragraph.find(qn("pPr"))
                if paragraph_properties is not None:
                    style = paragraph_properties.find(qn("pStyle"))
                    if style is not None:
                        paragraph_style = style.get(qn("val"), "")
                for run in paragraph.iter(qn("r")):
                    run_text = ooxml_run_text(run)
                    if not run_text:
                        continue
                    run_start = offset
                    text_chunks.append(run_text)
                    offset += len(run_text)
                    run_properties = run.find(qn("rPr"))
                    if run_properties is None:
                        continue
                    highlight = run_properties.find(qn("highlight"))
                    if highlight is not None:
                        value = highlight.get(qn("val"), "")
                        color = {
                            "yellow": WD_YELLOW,
                            "cyan": WD_TURQUOISE,
                            "turquoise": WD_TURQUOISE,
                        }.get(value)
                        if color is not None:
                            if (
                                highlights
                                and highlights[-1]["end"] == run_start
                                and highlights[-1]["color"] == color
                            ):
                                highlights[-1]["end"] = offset
                                highlights[-1]["text"] += run_text
                            else:
                                highlights.append({
                                    "start": run_start,
                                    "end": offset,
                                    "color": color,
                                    "text": run_text,
                                })
                    small_caps = run_properties.find(qn("smallCaps"))
                    if (
                        small_caps is not None
                        and small_caps.get(qn("val"), "true")
                        not in {"false", "0", "off"}
                    ):
                        smallcaps.append((run_start, offset))
                    vertical = run_properties.find(qn("vertAlign"))
                    if (
                        vertical is not None
                        and vertical.get(qn("val")) == "superscript"
                    ):
                        superscript.append((run_start, offset))
                text_chunks.append("\r")
                offset += 1
                paragraphs.append({
                    "index": paragraph_index,
                    "start": paragraph_start,
                    "end": offset,
                    "style": paragraph_style,
                })
            stories[f"xml:{part_name}"] = {
                "story_type": part_name,
                "text": "".join(text_chunks),
                "paragraphs": paragraphs,
                "highlights": highlights,
                "smallcaps": smallcaps,
                "superscript": superscript,
            }
    return stories


def property_runs(
    paragraph_range: Any,
    story_start: int,
    property_name: str,
) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []

    def read_value(start: int, end: int) -> int:
        target = paragraph_range.Duplicate
        target.SetRange(start, end)
        if property_name == "highlight":
            value = target.HighlightColorIndex
        else:
            value = getattr(target.Font, property_name)
        target = None
        return int(value)

    def visit(start: int, end: int) -> None:
        if end <= start:
            return
        value = read_value(start, end)
        if value != WD_UNDEFINED:
            runs.append((start - story_start, end - story_start, value))
            return
        if end - start == 1:
            runs.append((start - story_start, end - story_start, value))
            return
        middle = start + (end - start) // 2
        visit(start, middle)
        visit(middle, end)

    visit(paragraph_range.Start, paragraph_range.End)
    merged: list[tuple[int, int, int]] = []
    for start, end, value in runs:
        if merged and merged[-1][1] == start and merged[-1][2] == value:
            merged[-1] = (merged[-1][0], end, value)
        else:
            merged.append((start, end, value))
    return merged


def find_highlight_runs(story: Any) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []
    story_start = story.Start
    story_end = story.End
    search_start = story_start
    while search_start < story_end:
        target = story.Duplicate
        target.SetRange(search_start, story_end)
        finder = target.Find
        finder.ClearFormatting()
        finder.Replacement.ClearFormatting()
        finder.Text = ""
        finder.Forward = True
        finder.Wrap = 0
        finder.Format = True
        finder.Highlight = True
        if not finder.Execute():
            break
        if target.End <= search_start:
            search_start += 1
            continue
        color = int(target.HighlightColorIndex)
        if color in (WD_YELLOW, WD_TURQUOISE):
            runs.append((
                target.Start - story_start,
                target.End - story_start,
                color,
            ))
        search_start = target.End
        target = None
    return runs


def snapshot_document(
    path: Path,
    *,
    collect_highlights: bool,
    collect_character_styles: bool,
    collect_paragraph_styles: bool,
) -> dict[str, Any]:
    word = word_application()
    document = None
    try:
        document = word.Documents.Open(
            FileName=str(path),
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )
        print(f"snapshot opened: {path.name}", flush=True)
        word_story_hashes: dict[str, str] = {}
        for story_key, story_type, story in iter_story_ranges(document):
            story_text = story.Text
            word_story_hashes[story_key] = hashlib.sha256(
                story_text.encode("utf-8", "surrogatepass")
            ).hexdigest()
            story = None
        print(f"snapshot stories done: {path.name}", flush=True)

        header_footer_signature = []
        for section_index in range(1, document.Sections.Count + 1):
            section = document.Sections(section_index)
            for collection_name in ("Headers", "Footers"):
                collection = getattr(section, collection_name)
                for item_index in range(1, collection.Count + 1):
                    item = collection(item_index)
                    text = item.Range.Text if item.Exists else ""
                    header_footer_signature.append({
                        "section": section_index,
                        "kind": collection_name,
                        "index": item_index,
                        "exists": bool(item.Exists),
                        "text_sha256": hashlib.sha256(
                            text.encode("utf-8", "surrogatepass")
                        ).hexdigest(),
                    })
                    item = None
            section = None

        stories = ooxml_stories(path)
        highlight_total = Counter(
            item["color"]
            for story in stories.values()
            for item in story["highlights"]
        )
        if not collect_highlights:
            for story in stories.values():
                story["highlights"] = []
        if not collect_character_styles:
            for story in stories.values():
                story["smallcaps"] = []
                story["superscript"] = []
        if not collect_paragraph_styles:
            for story in stories.values():
                for paragraph in story["paragraphs"]:
                    paragraph["style"] = ""

        return {
            "opened": True,
            "sections": document.Sections.Count,
            "tables": document.Tables.Count,
            "footnotes": document.Footnotes.Count,
            "endnotes": document.Endnotes.Count,
            "inline_shapes": document.InlineShapes.Count,
            "shapes": document.Shapes.Count,
            "headers_footers": header_footer_signature,
            "stories": stories,
            "word_story_hashes": word_story_hashes,
            "yellow_range_count": highlight_total[WD_YELLOW],
            "turquoise_range_count": highlight_total[WD_TURQUOISE],
        }
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def overlaps(
    ranges: list[dict[str, Any]],
    start: int,
    end: int,
    color: int,
) -> bool:
    if end > start:
        return any(
            item["color"] == color
            and item["start"] < end
            and item["end"] > start
            for item in ranges
        )
    return any(
        item["color"] == color
        and item["start"] <= start < item["end"]
        for item in ranges
    ) or any(
        item["color"] == color
        and item["start"] < start <= item["end"]
        for item in ranges
    )


def audit_visible_changes(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[dict[str, Any]]:
    silent: list[dict[str, Any]] = []
    all_story_keys = sorted(set(before["stories"]) | set(after["stories"]))
    for story_key in all_story_keys:
        old = before["stories"].get(story_key, {"text": ""})
        new = after["stories"].get(
            story_key,
            {"text": "", "highlights": [], "paragraphs": []},
        )
        matcher = difflib.SequenceMatcher(
            a=old["text"],
            b=new["text"],
            autojunk=True,
        )
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            if not overlaps(new["highlights"], j1, j2, WD_YELLOW):
                silent.append({
                    "kind": "text",
                    "story": story_key,
                    "old_start": i1,
                    "old_end": i2,
                    "new_start": j1,
                    "new_end": j2,
                })

        old_paragraphs = old.get("paragraphs", [])
        new_paragraphs = new.get("paragraphs", [])
        for old_paragraph, new_paragraph in zip(old_paragraphs, new_paragraphs):
            if old_paragraph["style"] == new_paragraph["style"]:
                continue
            start = new_paragraph["start"]
            end = new_paragraph["end"]
            if not overlaps(new["highlights"], start, end, WD_YELLOW):
                silent.append({
                    "kind": "paragraph_style",
                    "story": story_key,
                    "paragraph": new_paragraph["index"],
                })

        for property_name in ("smallcaps", "superscript"):
            old_ranges = set(map(tuple, old.get(property_name, [])))
            for start, end in new.get(property_name, []):
                if (start, end) in old_ranges:
                    continue
                if not overlaps(new["highlights"], start, end, WD_YELLOW):
                    silent.append({
                        "kind": property_name,
                        "story": story_key,
                        "start": start,
                        "end": end,
                    })
    return silent


def preservation(before: dict[str, Any], after: dict[str, Any]) -> dict[str, bool]:
    before_header_footer_presence = [
        {
            "section": item["section"],
            "kind": item["kind"],
            "index": item["index"],
            "exists": item["exists"],
        }
        for item in before["headers_footers"]
    ]
    after_header_footer_presence = [
        {
            "section": item["section"],
            "kind": item["kind"],
            "index": item["index"],
            "exists": item["exists"],
        }
        for item in after["headers_footers"]
    ]
    return {
        "sections_preserved": before["sections"] == after["sections"],
        "tables_preserved": before["tables"] == after["tables"],
        "footnotes_preserved": before["footnotes"] == after["footnotes"],
        "endnotes_preserved": before["endnotes"] == after["endnotes"],
        "images_objects_preserved": (
            before["inline_shapes"] == after["inline_shapes"]
            and before["shapes"] == after["shapes"]
        ),
        "headers_footers_preserved": (
            before_header_footer_presence == after_header_footer_presence
        ),
    }


def highlight_context_rows(
    source_kind: str,
    source_file: str,
    pass_name: str,
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for story_key, story in snapshot["stories"].items():
        text = story["text"]
        for highlight in story["highlights"]:
            start = highlight["start"]
            end = highlight["end"]
            paragraph_index = ""
            for paragraph in story["paragraphs"]:
                if paragraph["start"] <= start < paragraph["end"]:
                    paragraph_index = paragraph["index"]
                    break
            rows.append({
                "source_kind": source_kind,
                "source_file": source_file,
                "pass": pass_name,
                "story": story_key,
                "paragraph_index": paragraph_index,
                "highlight": (
                    "yellow"
                    if highlight["color"] == WD_YELLOW
                    else "turquoise"
                ),
                "context_before": text[max(0, start - 80) : start]
                .replace("\r", " ")
                .replace("\t", " "),
                "highlighted_text": highlight["text"]
                .replace("\r", " ")
                .replace("\t", " "),
                "context_after": text[end : end + 80]
                .replace("\r", " ")
                .replace("\t", " "),
            })
    return rows


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    first_totals = Counter()
    second_totals = Counter()
    successes = 0
    failures = 0
    yellow = 0
    turquoise = 0
    silent = 0
    for record in records:
        if record.get("error"):
            failures += 1
            continue
        successes += 1
        first_totals.update(record["first_pass_counts"])
        second_totals.update(record["second_pass_counts"])
        yellow += record["yellow_range_count"]
        turquoise += record["turquoise_range_count"]
        silent += record["silent_change_count"]
    exercised = sorted(rule_id for rule_id in RULE_IDS if first_totals[rule_id])
    not_exercised = sorted(set(RULE_IDS) - set(exercised))
    return {
        "documents": len(records),
        "successes": successes,
        "failures": failures,
        "first_pass_totals": dict(sorted(first_totals.items())),
        "second_pass_totals": dict(sorted(second_totals.items())),
        "rules_exercised": exercised,
        "rules_not_exercised": not_exercised,
        "yellow_range_count": yellow,
        "turquoise_range_count": turquoise,
        "silent_change_count": silent,
    }


def write_reports(
    records: list[dict[str, Any]],
    contexts: list[dict[str, Any]],
) -> None:
    aggregate_data = aggregate(records)
    payload = {
        "rule_ids": list(RULE_IDS),
        "automatic_rule_ids": sorted(AUTOMATIC_RULE_IDS),
        "diagnostic_rule_ids": sorted(DIAGNOSTIC_RULE_IDS),
        "pipeline_rule_ids": sorted(PIPELINE_RULE_IDS),
        "aggregate": aggregate_data,
        "documents": records,
    }
    (REPORT_ROOT / "validation_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (REPORT_ROOT / "highlighted_contexts.tsv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "source_kind",
                "source_file",
                "pass",
                "story",
                "paragraph_index",
                "highlight",
                "context_before",
                "highlighted_text",
                "context_after",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(contexts)

    lines = [
        "# Validation reborn — étape 5",
        "",
        f"- Documents traités : {aggregate_data['documents']}",
        f"- Succès : {aggregate_data['successes']}",
        f"- Échecs : {aggregate_data['failures']}",
        f"- Règles exercées : {len(aggregate_data['rules_exercised'])}",
        f"- Règles non exercées : {len(aggregate_data['rules_not_exercised'])}",
        f"- Plages jaunes : {aggregate_data['yellow_range_count']}",
        f"- Plages turquoise : {aggregate_data['turquoise_range_count']}",
        f"- Modifications silencieuses : {aggregate_data['silent_change_count']}",
        "",
        "## Totaux du premier passage",
        "",
    ]
    lines.extend(
        f"- `{rule_id}` : {aggregate_data['first_pass_totals'].get(rule_id, 0)}"
        for rule_id in RULE_IDS
    )
    lines.extend([
        "",
        "## Totaux du second passage",
        "",
    ])
    lines.extend(
        f"- `{rule_id}` : {aggregate_data['second_pass_totals'].get(rule_id, 0)}"
        for rule_id in RULE_IDS
    )
    lines.extend([
        "",
        "## Règles non exercées",
        "",
    ])
    lines.extend(
        f"- `{rule_id}` — `not_exercised_on_private_corpus`"
        for rule_id in aggregate_data["rules_not_exercised"]
    )
    lines.extend([
        "",
        "## Transformations sur les copies éditées",
        "",
    ])
    output_records = [
        record
        for record in records
        if record["source_kind"] == "output_samples" and not record.get("error")
    ]
    for record in output_records:
        changes = record["classification_of_changes_on_edited_copy"]
        if changes:
            lines.append(
                f"- `{record['input_file']}` : "
                + ", ".join(
                    f"`{item['rule_id']}` ({item['count']}, {item['classification']})"
                    for item in changes
                )
            )
    lines.extend([
        "",
        "## Incidents",
        "",
    ])
    for record in records:
        if record.get("error"):
            lines.append(f"- `{record['input_file']}` : {record['error']}")
        elif (
            record["silent_change_count"]
            or not all(record["preservation"].values())
            or record["automatic_second_pass_nonzero"]
        ):
            lines.append(
                f"- `{record['input_file']}` : "
                f"silent={record['silent_change_count']}, "
                f"préservation={record['preservation']}, "
                f"second_pass_auto={record['automatic_second_pass_nonzero']}"
            )
    if lines[-1] == "## Incidents":
        lines.extend(["", "- Aucun incident."])
    (REPORT_ROOT / "validation_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if REPORT_ROOT != EXPECTED_REPORT_ROOT:
        raise RuntimeError(f"Cible inattendue : {REPORT_ROOT}")
    private_reports = (PRIVATE_ROOT / "private_reports").resolve()
    if REPORT_ROOT.parent != private_reports or REPORT_ROOT.name != "reborn_step5":
        raise RuntimeError(f"Nettoyage refusé hors cible : {REPORT_ROOT}")
    if REPORT_ROOT.exists():
        shutil.rmtree(REPORT_ROOT)
    for source_kind in SOURCE_ROOTS:
        (REPORT_ROOT / source_kind / "first_pass").mkdir(
            parents=True,
            exist_ok=True,
        )
        (REPORT_ROOT / source_kind / "second_pass").mkdir(
            parents=True,
            exist_ok=True,
        )

    records: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    for source_kind, source_root in SOURCE_ROOTS.items():
        for input_path in selected_docx(source_root):
            relative = input_path.relative_to(source_root)
            first_output = (
                REPORT_ROOT / source_kind / "first_pass" / relative
            )
            second_output = (
                REPORT_ROOT / source_kind / "second_pass" / relative
            )
            first_output.parent.mkdir(parents=True, exist_ok=True)
            second_output.parent.mkdir(parents=True, exist_ok=True)
            record: dict[str, Any] = {
                "input_file": relative.as_posix(),
                "source_kind": source_kind,
                "input_sha256_before": sha256(input_path),
                "first_pass_output": str(first_output),
                "second_pass_output": str(second_output),
            }
            try:
                before = snapshot_document(
                    input_path,
                    collect_highlights=False,
                    collect_character_styles=True,
                    collect_paragraph_styles=False,
                )
                first_counts = correct_docx(input_path, first_output)
                structure_changed = any(
                    first_counts[rule_id] for rule_id in STRUCTURE_RULE_IDS
                )
                first = snapshot_document(
                    first_output,
                    collect_highlights=True,
                    collect_character_styles=True,
                    collect_paragraph_styles=structure_changed,
                )
                second_counts = correct_docx(first_output, second_output)
                second = snapshot_document(
                    second_output,
                    collect_highlights=True,
                    collect_character_styles=False,
                    collect_paragraph_styles=structure_changed,
                )
                record["input_sha256_after"] = sha256(input_path)
                silent = audit_visible_changes(before, first)
                preservation_result = preservation(before, first)
                automatic_second_pass_nonzero = {
                    rule_id: second_counts[rule_id]
                    for rule_id in sorted(AUTOMATIC_RULE_IDS)
                    if second_counts[rule_id]
                }
                diagnostic_stability = {
                    rule_id: (
                        first_counts[rule_id],
                        second_counts[rule_id],
                    )
                    for rule_id in sorted(
                        DIAGNOSTIC_RULE_IDS | PIPELINE_RULE_IDS
                    )
                    if first_counts[rule_id] != second_counts[rule_id]
                }
                classifications = []
                if source_kind == "output_samples":
                    for rule_id in sorted(AUTOMATIC_RULE_IDS):
                        count = first_counts[rule_id]
                        if count:
                            classifications.append({
                                "rule_id": rule_id,
                                "count": count,
                                "classification": "undetermined",
                            })
                record.update({
                    "first_pass_counts": first_counts,
                    "second_pass_counts": second_counts,
                    "yellow_range_count": first["yellow_range_count"],
                    "turquoise_range_count": first["turquoise_range_count"],
                    "document_opened": first["opened"] and second["opened"],
                    **preservation_result,
                    "preservation": preservation_result,
                    "silent_change_count": len(silent),
                    "silent_changes": silent,
                    "automatic_second_pass_nonzero": (
                        automatic_second_pass_nonzero
                    ),
                    "diagnostic_pipeline_instability": diagnostic_stability,
                    "yellow_preserved_second_pass": (
                        second["yellow_range_count"]
                        >= first["yellow_range_count"]
                    ),
                    "classification_of_changes_on_edited_copy": classifications,
                })
                contexts.extend(
                    highlight_context_rows(
                        source_kind,
                        relative.as_posix(),
                        "first_pass",
                        first,
                    )
                )
                contexts.extend(
                    highlight_context_rows(
                        source_kind,
                        relative.as_posix(),
                        "second_pass",
                        second,
                    )
                )
            except Exception as exc:
                record["input_sha256_after"] = sha256(input_path)
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["traceback"] = traceback.format_exc(limit=8)
            records.append(record)
            print(
                f"{source_kind}: {relative.as_posix()} "
                f"{'FAIL' if record.get('error') else 'OK'}",
                flush=True,
            )
            write_reports(records, contexts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
