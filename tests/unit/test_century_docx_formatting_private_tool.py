from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from purh_editorial.model import Block, Document, InlineSpan, InlineStyle
from purh_editorial.rules.model import ProposedAction, RuleActionType


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools/analyze_century_docx_formatting_private.py"


def _tool():
    name = "century_formatting_private_tool_test"
    spec = importlib.util.spec_from_file_location(name, TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _segments(*, small_caps=True, superscript=True, suffix="e", revision=None):
    return [
        {
            "text": "xvii",
            "relative_start": 0,
            "relative_end": 4,
            "small_caps": small_caps,
            "caps": None,
            "superscript": None,
            "subscript": None,
            "bold": None,
            "italic": None,
            "style_name": "",
            "revision_kind": revision,
        },
        {
            "text": suffix,
            "relative_start": 4,
            "relative_end": 5,
            "small_caps": None,
            "caps": None,
            "superscript": superscript,
            "subscript": None,
            "bold": None,
            "italic": None,
            "style_name": "",
            "revision_kind": revision,
        },
    ]


def _classify(tool, *, before="xviie", segments=None, target="au xviie siècle"):
    start = target.index(before)
    return tool.classify_century_occurrence(
        text_before=before,
        target_text=target,
        offset_start=start,
        offset_end=start + len(before),
        segments=_segments() if segments is None else segments,
    )


def test_compliant_requires_effective_small_caps_and_superscript() -> None:
    tool = _tool()
    assert _classify(tool)[:2] == ("compliant_purh_styled", "none")
    assert _classify(tool, segments=_segments(small_caps=False))[0] == "noncompliant_missing_or_wrong_styling"
    assert _classify(tool, segments=_segments(superscript=False))[0] == "noncompliant_missing_or_wrong_styling"


def test_partial_unset_and_contradictory_styles_are_not_silently_accepted() -> None:
    tool = _tool()
    partial = _segments()
    partial[0]["small_caps"] = None
    assert _classify(tool, segments=partial)[0] == "indeterminate"
    partial_roman = _segments()
    partial_roman.insert(
        1, {**partial_roman[0], "text": "ii", "relative_start": 2, "relative_end": 4, "small_caps": False})
    partial_roman[0]["text"] = "xv"
    partial_roman[0]["relative_end"] = 2
    assert _classify(tool, segments=partial_roman)[0] == "noncompliant_missing_or_wrong_styling"
    suffix_unset = _segments(superscript=None)
    assert _classify(tool, segments=suffix_unset)[0] == "indeterminate"
    contradictory = _segments()
    contradictory[0]["caps"] = True
    assert _classify(tool, segments=contradictory)[0] == "noncompliant_missing_or_wrong_styling"
    split = _segments()
    split[0]["text"] = "xv"
    split[0]["relative_end"] = 2
    split.insert(1, {**_segments()[0], "text": "ii", "relative_start": 2, "relative_end": 4})
    assert _classify(tool, segments=split)[:2] == ("compliant_purh_styled", "none")


def test_long_suffix_revisions_and_ambiguous_coverage_are_deterministic() -> None:
    tool = _tool()
    assert _classify(tool, before="XVIIème", segments=[{**_segments()[0], "text": "XVII", "relative_end": 4}, {**_segments()[1], "text": "ème", "relative_start": 4, "relative_end": 7}], target="au XVIIème siècle")[:2] == ("noncompliant_textual_form", "transformation_and_styling")
    assert _classify(tool, segments=_segments(revision="insertion"))[0] == "indeterminate"
    assert _classify(tool, segments=_segments(revision="deletion"))[0] == "indeterminate"
    assert _classify(tool, segments=[])[0] == "indeterminate"


def test_character_style_inheritance_is_resolved_without_collapsing_unset() -> None:
    tool = _tool()
    styles = ET.fromstring(
        """
        <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:style w:type="character" w:styleId="base"><w:name w:val="Base"/><w:rPr><w:smallCaps/></w:rPr></w:style>
          <w:style w:type="character" w:styleId="century"><w:name w:val="Century"/><w:basedOn w:val="base"/></w:style>
        </w:styles>
        """
    )
    resolver = tool._StyleResolver(ET.tostring(styles))
    paragraph = ET.fromstring('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
    run = ET.fromstring('<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:rPr><w:rStyle w:val="century"/></w:rPr><w:t>xvii</w:t></w:r>')
    properties = resolver.resolve_run(run, paragraph)
    assert properties["small_caps"] is True
    assert properties["superscript"] is None


def test_historical_four_j_bis_condition_is_exact_and_does_not_use_text_alone() -> None:
    tool = _tool()
    action = ProposedAction(
        action_type=RuleActionType.TEXT_TRANSFORM,
        target_refs=("p1",),
        before="xviie",
        after="XVIIe",
        offset_start=3,
        offset_end=8,
    )
    styled = [
        InlineSpan(text="au "),
        InlineSpan(text="xvii", style=InlineStyle(small_caps=True)),
        InlineSpan(text="e", style=InlineStyle(superscript=True)),
        InlineSpan(text=" siècle"),
    ]
    document = Document("d", "source.docx", "docx", blocks=[Block("p1", "paragraph", "au xviie siècle", styled)])
    assert tool.four_j_bis_would_filter(action=action, document=document, target_ref="p1", target_text="au xviie siècle")
    document.blocks[0].inlines[1].style.small_caps = False
    assert not tool.four_j_bis_would_filter(action=action, document=document, target_ref="p1", target_text="au xviie siècle")
