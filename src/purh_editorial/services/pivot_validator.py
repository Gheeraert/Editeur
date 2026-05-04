from __future__ import annotations

import re

from purh_editorial.model import Diagnostic, Document, Evidence
from purh_editorial.model.semantics import (
    extract_verse_lines,
    is_canonical_lineated_block,
    is_canonical_poetry_block,
    read_block_semantics,
)
from purh_editorial.utils import make_id

_CHRONOLOGY_LINE_RE = re.compile(r"^\s*(?:\d{1,4}|[IVXLCDM]+)\s*(?:[-–—.:)]|\b)", re.IGNORECASE)


class PivotValidator:
    module_name = "pivot_validator"

    def validate(self, document: Document) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for block in document.blocks:
            semantics = read_block_semantics(block)
            semantic_payload = (block.attributes or {}).get("semantic")
            semantic_payload = semantic_payload if isinstance(semantic_payload, dict) else {}
            text_excerpt = (block.text or "")[:220]
            is_lineated = is_canonical_lineated_block(block)

            if block.block_type == "heading":
                raw_level = block.attributes.get("heading_level")
                if not isinstance(raw_level, int) or not (1 <= raw_level <= 6):
                    diagnostics.append(
                        self._diag(
                            block.block_id,
                            "error",
                            "pivot_invariant",
                            "Heading sans heading_level valide.",
                            "pivot.heading.level.required",
                            text_excerpt,
                        )
                    )

            if semantics.quote_kind and semantics.role != "quote":
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "quote_kind present hors role=quote.",
                        "pivot.semantic.quote_fields_on_non_quote",
                        text_excerpt,
                    )
                )

            if (
                semantics.role == "lineated_block"
                and block.block_type != "lineated_block"
            ):
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "role=lineated_block exige block_type=lineated_block.",
                        "pivot.semantic.lineated_block_role_mismatch",
                        text_excerpt,
                    )
                )

            if semantics.lineation == "lineated" and not semantics.lines:
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "lineation=lineated exige des lignes non vides.",
                        "pivot.semantic.lineation_without_lines",
                        text_excerpt,
                    )
                )

            if semantics.role == "lineated_block" and semantics.lineation != "lineated":
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "role=lineated_block exige lineation=lineated.",
                        "pivot.semantic.lineated_block_without_lineation",
                        text_excerpt,
                    )
                )

            if semantics.role == "lineated_block" and not semantics.lines:
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "role=lineated_block exige des lignes non vides.",
                        "pivot.semantic.lineated_block_without_lines",
                        text_excerpt,
                    )
                )

            if semantics.lines and semantics.lineation != "lineated":
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "Lignes presentes hors lineation=lineated.",
                        "pivot.semantic.lines_on_non_poetry",
                        text_excerpt,
                    )
                )

            if (
                semantics.lineation == "lineated"
                and block.block_type not in {"lineated_block", "quote_block"}
            ):
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "lineation=lineated hors block_type lineated_block/quote_block.",
                        "pivot.semantic.verse_on_non_poetry",
                        text_excerpt,
                    )
                )

            if is_lineated:
                lines = semantics.lines or extract_verse_lines(block)
                if not lines:
                    diagnostics.append(
                        self._diag(
                            block.block_id,
                            "error",
                            "pivot_invariant",
                            "Bloc lineate canonique sans lignes exploitables.",
                            "pivot.poetry.lines.required",
                            text_excerpt,
                        )
                    )
                elif is_canonical_poetry_block(block) and self._looks_like_chronology(lines):
                    diagnostics.append(
                        self._diag(
                            block.block_id,
                            "warning",
                            "pivot_suspicion",
                            "Bloc poetique canonique ressemblant a une chronologie/liste datee.",
                            "pivot.poetry.suspicious_chronology",
                            " | ".join(lines[:3])[:220],
                        )
                    )

            raw_quote_kind = semantic_payload.get("quote_kind")
            raw_lineation = semantic_payload.get("lineation")
            if (
                isinstance(raw_quote_kind, str)
                and raw_quote_kind.strip() == "poetry"
                and isinstance(raw_lineation, str)
                and raw_lineation.strip() == "verse"
            ):
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "warning",
                        "pivot_legacy",
                        "Payload semantic legacy quote_kind=poetry + lineation=verse detecte.",
                        "pivot.semantic.quote_kind_used_as_lineation_legacy",
                        text_excerpt,
                    )
                )
        return diagnostics

    @staticmethod
    def _looks_like_chronology(lines: list[str]) -> bool:
        if len(lines) < 2:
            return False
        matched = sum(1 for line in lines if _CHRONOLOGY_LINE_RE.match(line.strip()))
        return matched >= max(2, len(lines) - 1)

    def _diag(
        self,
        target_ref: str,
        severity: str,
        category: str,
        message: str,
        rule_id: str,
        excerpt: str,
    ) -> Diagnostic:
        return Diagnostic(
            diagnostic_id=make_id("diag"),
            module=self.module_name,
            severity=severity,
            category=category,
            message=message,
            target_ref=target_ref,
            rule_id=rule_id,
            evidence=Evidence(excerpt=excerpt),
        )
