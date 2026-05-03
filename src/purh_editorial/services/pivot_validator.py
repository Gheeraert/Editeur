from __future__ import annotations

import re

from purh_editorial.model import Diagnostic, Document, Evidence
from purh_editorial.model.semantics import (
    extract_verse_lines,
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
            semantics = read_block_semantics(block, allow_legacy_inference=False)
            text_excerpt = (block.text or "")[:220]

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

            if block.block_type != "quote_block" and (semantics.quote_kind or semantics.lineation):
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "Champs de citation presents sur un bloc non quote_block.",
                        "pivot.semantic.quote_fields_on_non_quote",
                        text_excerpt,
                    )
                )

            if semantics.lineation == "verse" and not is_canonical_poetry_block(block):
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "lineation=verse hors poesie canonique.",
                        "pivot.semantic.verse_on_non_poetry",
                        text_excerpt,
                    )
                )

            if semantics.quote_kind == "poetry" and semantics.lineation != "verse":
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "quote_kind=poetry exige lineation=verse.",
                        "pivot.poetry.quote_kind.requires_verse",
                        text_excerpt,
                    )
                )

            if semantics.lines and not is_canonical_poetry_block(block):
                diagnostics.append(
                    self._diag(
                        block.block_id,
                        "error",
                        "pivot_invariant",
                        "Lignes de vers presentes hors poesie canonique.",
                        "pivot.semantic.lines_on_non_poetry",
                        text_excerpt,
                    )
                )

            if is_canonical_poetry_block(block):
                lines = semantics.lines or extract_verse_lines(block)
                if not lines:
                    diagnostics.append(
                        self._diag(
                            block.block_id,
                            "error",
                            "pivot_invariant",
                            "Bloc poetique canonique sans lignes de vers exploitables.",
                            "pivot.poetry.lines.required",
                            text_excerpt,
                        )
                    )
                elif self._looks_like_chronology(lines):
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
