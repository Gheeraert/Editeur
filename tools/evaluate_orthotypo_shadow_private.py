"""Banc local d'observation shadow pour deux règles orthotypographiques.

Ce script est volontairement hors pipeline. Il ne modifie aucun DOCX : chaque
adaptateur conserve le legacy comme seule source d'effets et le natif reste
observé uniquement.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from purh_editorial.config.private_corpus import (  # noqa: E402
    ENV_VAR,
    resolve_private_corpus_dir,
)
from purh_editorial.io.importer_registry import ImporterRegistry  # noqa: E402
from purh_editorial.model import Document  # noqa: E402
from purh_editorial.rules.model import DecisionOutcome, ProposedAction  # noqa: E402
from purh_editorial.rules.orthotypography.etc_rule import (  # noqa: E402
    RULE_ID as ETC_RULE_ID,
    EtcAbbreviationRule,
)
from purh_editorial.rules.orthotypography.redoublement_rule import (  # noqa: E402
    RULE_ID as REDOUBLEMENT_RULE_ID,
    RedoubledAbbreviationRule,
)
from purh_editorial.rules.shadow import (  # noqa: E402
    LegacyObservationStatus,
    ShadowComparisonStatus,
)
from purh_editorial.services.orthotypo_redoublement_shadow_adapter import (  # noqa: E402
    OrthotypoRedoublementShadowAdapter,
)
from purh_editorial.services.orthotypo_shadow_adapter import (  # noqa: E402
    OrthotypoEtcShadowAdapter,
)
from purh_editorial.services.orthotypo_shadow_support import (  # noqa: E402
    collect_orthotypo_shadow_targets,
    find_legacy_orthotypo_rule_index,
    reconstruct_pre_rule_text,
)


RULE_IDS = (ETC_RULE_ID, REDOUBLEMENT_RULE_ID)
_METHODOLOGY_WARNING = (
    "Cette comparaison de corpus n’aligne pas automatiquement les passages "
    "auteur et corrigés. Elle mesure la parité legacy/natif et la présence "
    "résiduelle des motifs ; elle ne permet pas, à elle seule, d’affirmer "
    "qu’une correction précise a été acceptée ou refusée par les éditrices."
)


class EvaluationInputError(ValueError):
    """Les chemins fournis ne respectent pas la frontière privée."""


class EvaluationInvariantError(RuntimeError):
    """Un adaptateur shadow a produit un résultat incohérent."""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolved_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _validate_paths(
    *,
    raw_docx: str | Path,
    reference_dir: str | Path,
    output_dir: str | Path,
) -> tuple[Path, Path, Path, tuple[Path, ...]]:
    private_root = resolve_private_corpus_dir()
    if private_root is None:
        raise EvaluationInputError(
            f"{ENV_VAR} doit pointer vers un dossier privé existant."
        )
    private_root = private_root.resolve()
    raw_path = _resolved_path(raw_docx)
    references_path = _resolved_path(reference_dir)
    report_path = _resolved_path(output_dir)

    if not raw_path.is_file():
        raise EvaluationInputError("Le manuscrit auteur DOCX doit exister.")
    if raw_path.suffix.lower() != ".docx":
        raise EvaluationInputError("Le manuscrit auteur doit avoir l’extension .docx.")
    if not references_path.is_dir():
        raise EvaluationInputError("Le dossier des copies corrigées doit exister.")
    if _is_within(report_path, REPOSITORY_ROOT.resolve()):
        raise EvaluationInputError(
            "Le dossier de sortie doit être situé hors du dépôt Git."
        )
    if not all(
        _is_within(path, private_root)
        for path in (raw_path, references_path, report_path)
    ):
        raise EvaluationInputError(
            "Les entrées et la sortie doivent rester dans le corpus privé configuré."
        )

    references = tuple(
        sorted(
            (
                path
                for path in references_path.rglob("*")
                if path.is_file() and path.suffix.lower() == ".docx"
            ),
            key=lambda path: str(path).casefold(),
        )
    )
    if not references:
        raise EvaluationInputError(
            "Le dossier des copies corrigées doit contenir au moins un DOCX."
        )
    return raw_path, references_path, report_path, references


def _empty_rule_summary() -> dict[str, Any]:
    return {
        "targets": 0,
        "decisions": 0,
        "comparisons": 0,
        "decision_outcomes": {
            outcome.value: 0 for outcome in DecisionOutcome
        },
        "comparison_statuses": {
            status.value: 0 for status in ShadowComparisonStatus
        },
        "native_actions_proposed": 0,
        "legacy_actions_observed": 0,
        "protected_proposals": 0,
        "legacy_observations_failed": 0,
    }


def _action_data(action: ProposedAction, pre_rule_text: str) -> dict[str, Any]:
    excerpt: str | None = None
    if action.offset_start is not None and action.offset_end is not None:
        start = action.offset_start
        end = action.offset_end
        before = pre_rule_text[max(0, start - 40) : start]
        occurrence = pre_rule_text[start:end]
        after = pre_rule_text[end : end + 40]
        excerpt = (before + "[" + occurrence + "]" + after).replace(
            "\n", " "
        ).replace("\r", " ")
    return {
        "action_type": action.action_type.value,
        "before": action.before,
        "after": action.after,
        "offset_start": action.offset_start,
        "offset_end": action.offset_end,
        "target_refs": list(action.target_refs),
        "context_excerpt": excerpt,
    }


def _summarize_rule(
    *,
    document: Document,
    document_kind: str,
    document_label: str,
    document_filename: str,
    result: Any,
    rule_id: str,
    protection_policy_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    targets = collect_orthotypo_shadow_targets(
        document,
        protection_policy_id=protection_policy_id,
    )
    decisions = result.native_decisions
    comparisons = result.comparisons
    if not (
        len(targets) == len(decisions) == len(comparisons)
    ):
        raise EvaluationInvariantError(
            "Le nombre de cibles, décisions et comparaisons doit concorder."
        )
    if result.rule_id != rule_id:
        raise EvaluationInvariantError("L’adaptateur a retourné une règle inattendue.")

    targets_by_ref = {target.target_ref: target for target in targets}
    rule_index = find_legacy_orthotypo_rule_index(rule_id)
    summary = _empty_rule_summary()
    summary["targets"] = len(targets)
    summary["decisions"] = len(decisions)
    summary["comparisons"] = len(comparisons)
    details: list[dict[str, Any]] = []

    for decision, comparison in zip(decisions, comparisons):
        if decision.rule_id != rule_id or comparison.rule_id != rule_id:
            raise EvaluationInvariantError("Une décision shadow porte une règle inattendue.")
        if len(decision.target_refs) != 1:
            raise EvaluationInvariantError("Chaque décision doit concerner une seule cible.")
        target_ref = decision.target_refs[0]
        target = targets_by_ref.get(target_ref)
        if target is None:
            raise EvaluationInvariantError("Une décision référence une cible inconnue.")

        summary["decision_outcomes"][decision.outcome.value] += 1
        summary["comparison_statuses"][comparison.status.value] += 1
        summary["native_actions_proposed"] += len(decision.proposed_actions)
        summary["legacy_actions_observed"] += len(
            comparison.legacy_observation.observed_actions
        )
        if target.protection.protected and decision.proposed_actions:
            summary["protected_proposals"] += 1
        if (
            comparison.legacy_observation.status
            is LegacyObservationStatus.FAILED
        ):
            summary["legacy_observations_failed"] += 1

        needs_detail = bool(decision.proposed_actions) or (
            comparison.status is not ShadowComparisonStatus.MATCH
        ) or (
            comparison.legacy_observation.status
            is not LegacyObservationStatus.COMPLETE
        )
        if not needs_detail:
            continue

        pre_rule_text = reconstruct_pre_rule_text(
            target.text,
            rule_index=rule_index,
        )
        details.append(
            {
                "document_kind": document_kind,
                "document_label": document_label,
                "document_filename": document_filename,
                "rule_id": rule_id,
                "target_ref": target_ref,
                "sequence": decision.sequence,
                "decision_outcome": decision.outcome.value,
                "comparison_status": comparison.status.value,
                "protection": {
                    "protected": target.protection.protected,
                    "reasons": list(target.protection.reasons),
                    "inherited_from": list(target.protection.inherited_from),
                },
                "actions_native": [
                    _action_data(action, pre_rule_text)
                    for action in decision.proposed_actions
                ],
                "actions_legacy_observed": [
                    _action_data(action, pre_rule_text)
                    for action in comparison.legacy_observation.observed_actions
                ],
                "difference_codes": [
                    difference.code.value for difference in comparison.differences
                ],
            }
        )
    return summary, details


def _evaluate_document(
    *,
    document: Document,
    document_kind: str,
    document_label: str,
    document_filename: str,
) -> dict[str, Any]:
    source_snapshot = copy.deepcopy(document)
    etc_result = OrthotypoEtcShadowAdapter().run(document)
    if document != source_snapshot:
        raise EvaluationInvariantError("L’adaptateur etc. a modifié le document importé.")
    redoublement_result = OrthotypoRedoublementShadowAdapter().run(document)
    if document != source_snapshot:
        raise EvaluationInvariantError(
            "L’adaptateur redoublement a modifié le document importé."
        )

    etc_summary, etc_details = _summarize_rule(
        document=document,
        document_kind=document_kind,
        document_label=document_label,
        document_filename=document_filename,
        result=etc_result,
        rule_id=ETC_RULE_ID,
        protection_policy_id=EtcAbbreviationRule.descriptor.protection_policy_id,
    )
    redoublement_summary, redoublement_details = _summarize_rule(
        document=document,
        document_kind=document_kind,
        document_label=document_label,
        document_filename=document_filename,
        result=redoublement_result,
        rule_id=REDOUBLEMENT_RULE_ID,
        protection_policy_id=(
            RedoubledAbbreviationRule.descriptor.protection_policy_id
        ),
    )
    return {
        "document_kind": document_kind,
        "document_label": document_label,
        "document_filename": document_filename,
        "rules": {
            ETC_RULE_ID: etc_summary,
            REDOUBLEMENT_RULE_ID: redoublement_summary,
        },
        "occurrences": [*etc_details, *redoublement_details],
    }


def _empty_aggregate() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "author": {rule_id: _empty_rule_summary() for rule_id in RULE_IDS},
        "edited_reference": {
            rule_id: _empty_rule_summary() for rule_id in RULE_IDS
        },
    }


def _add_summary(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in (
        "targets",
        "decisions",
        "comparisons",
        "native_actions_proposed",
        "legacy_actions_observed",
        "protected_proposals",
        "legacy_observations_failed",
    ):
        target[key] += source[key]
    for key in ("decision_outcomes", "comparison_statuses"):
        for name, value in source[key].items():
            target[key][name] += value


def _build_editorial_contrast(
    aggregate: dict[str, dict[str, dict[str, Any]]],
    documents: Sequence[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    contrast: dict[str, dict[str, int]] = {}
    for rule_id in RULE_IDS:
        author = aggregate["author"][rule_id]
        reference = aggregate["edited_reference"][rule_id]
        contrast[rule_id] = {
            "author_proposed_actions": author["native_actions_proposed"],
            "author_apply_decisions": author["decision_outcomes"][
                DecisionOutcome.APPLY.value
            ],
            "author_protected_proposals": author["protected_proposals"],
            "edited_reference_proposed_actions": reference[
                "native_actions_proposed"
            ],
            "edited_reference_apply_decisions": reference[
                "decision_outcomes"][DecisionOutcome.APPLY.value],
            "edited_reference_protected_proposals": reference[
                "protected_proposals"
            ],
            "edited_reference_documents_with_proposals": sum(
                document["rules"][rule_id]["native_actions_proposed"] > 0
                for document in documents
                if document["document_kind"] == "edited_reference"
            ),
        }
    return contrast


def evaluate_corpus(
    *,
    raw_docx: str | Path,
    reference_dir: str | Path,
    output_dir: str | Path,
) -> tuple[dict[str, Any], Path, Path]:
    raw_path, _references_path, report_path, reference_paths = _validate_paths(
        raw_docx=raw_docx,
        reference_dir=reference_dir,
        output_dir=output_dir,
    )
    report_path.mkdir(parents=True, exist_ok=True)
    importer = ImporterRegistry()

    raw_document = importer.load_document(raw_path)
    documents = [
        _evaluate_document(
            document=raw_document,
            document_kind="author",
            document_label="author-001",
            document_filename=raw_path.name,
        )
    ]
    for index, reference_path in enumerate(reference_paths, start=1):
        reference_document = importer.load_document(reference_path)
        documents.append(
            _evaluate_document(
                document=reference_document,
                document_kind="edited_reference",
                document_label=f"reference-{index:03d}",
                document_filename=reference_path.name,
            )
        )

    aggregate = _empty_aggregate()
    for document in documents:
        kind = document["document_kind"]
        for rule_id in RULE_IDS:
            _add_summary(aggregate[kind][rule_id], document["rules"][rule_id])
    report = {
        "schema_version": 1,
        "scope": {
            "rules": list(RULE_IDS),
            "author_documents": 1,
            "edited_reference_documents": len(reference_paths),
        },
        "aggregate": aggregate,
        "editorial_contrast": _build_editorial_contrast(aggregate, documents),
        "documents": documents,
    }
    json_path = report_path / "orthotypo_shadow_4g.json"
    markdown_path = report_path / "orthotypo_shadow_4g.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    return report, json_path, markdown_path


def _markdown_table(report: dict[str, Any], kind: str) -> list[str]:
    lines = [
        "| Règle | Actions proposées | APPLY | MATCH | DIVERGENCE | INCONCLUSIVE | Protégées | Échecs legacy |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rule_id in RULE_IDS:
        summary = report["aggregate"][kind][rule_id]
        outcomes = summary["decision_outcomes"]
        statuses = summary["comparison_statuses"]
        lines.append(
            "| {rule} | {actions} | {apply} | {match} | {divergence} | {inconclusive} | {protected} | {failed} |".format(
                rule=rule_id,
                actions=summary["native_actions_proposed"],
                apply=outcomes[DecisionOutcome.APPLY.value],
                match=statuses[ShadowComparisonStatus.MATCH.value],
                divergence=statuses[ShadowComparisonStatus.DIVERGENCE.value],
                inconclusive=statuses[ShadowComparisonStatus.INCONCLUSIVE.value],
                protected=summary["protected_proposals"],
                failed=summary["legacy_observations_failed"],
            )
        )
    return lines


def _markdown_occurrence(detail: dict[str, Any]) -> list[str]:
    lines = [
        "- `{label}` · `{rule}` · cible `{target}` · séquence {sequence} "
        "· décision `{outcome}` · comparaison `{comparison}`".format(
            label=detail["document_label"],
            rule=detail["rule_id"],
            target=detail["target_ref"],
            sequence=detail["sequence"],
            outcome=detail["decision_outcome"],
            comparison=detail["comparison_status"],
        )
    ]
    for label, actions in (
        ("native", detail["actions_native"]),
        ("legacy", detail["actions_legacy_observed"]),
    ):
        for action in actions:
            lines.append(
                "  - {label}: `{before}` → `{after}` (offsets {start}–{end}) ; `{excerpt}`".format(
                    label=label,
                    before=action["before"],
                    after=action["after"],
                    start=action["offset_start"],
                    end=action["offset_end"],
                    excerpt=action["context_excerpt"],
                )
            )
    if detail["difference_codes"]:
        lines.append(
            "  - différences : " + ", ".join(detail["difference_codes"])
        )
    return lines


def _render_detail_section(
    *,
    title: str,
    details: Sequence[dict[str, Any]],
) -> list[str]:
    lines = [f"## {title}", ""]
    if not details:
        return [*lines, "Aucune occurrence.", ""]
    for detail in details:
        lines.extend(_markdown_occurrence(detail))
    lines.append("")
    return lines


def _render_markdown(report: dict[str, Any]) -> str:
    documents = report["documents"]
    details = [
        detail for document in documents for detail in document["occurrences"]
    ]
    lines = [
        "# Banc shadow orthotypographique 4G",
        "",
        "## Périmètre",
        "",
        "Règles observées : `purh.abreviations.etc` et "
        "`purh.abreviations.redoublement`.",
        "",
        "## Avertissement méthodologique",
        "",
        _METHODOLOGY_WARNING,
        "",
        "## Manuscrit auteur",
        "",
        *_markdown_table(report, "author"),
        "",
        "## Copies corrigées",
        "",
        *_markdown_table(report, "edited_reference"),
        "",
        "## Contraste neutre par règle",
        "",
        "| Règle | Actions auteur | APPLY auteur | Protégées auteur | Actions corrigé | APPLY corrigé | Protégées corrigé | Copies avec propositions |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rule_id in RULE_IDS:
        contrast = report["editorial_contrast"][rule_id]
        lines.append(
            "| {rule} | {author_actions} | {author_apply} | {author_protected} | {reference_actions} | {reference_apply} | {reference_protected} | {documents} |".format(
                rule=rule_id,
                author_actions=contrast["author_proposed_actions"],
                author_apply=contrast["author_apply_decisions"],
                author_protected=contrast["author_protected_proposals"],
                reference_actions=contrast["edited_reference_proposed_actions"],
                reference_apply=contrast[
                    "edited_reference_apply_decisions"
                ],
                reference_protected=contrast[
                    "edited_reference_protected_proposals"
                ],
                documents=contrast[
                    "edited_reference_documents_with_proposals"
                ],
            )
        )
    lines.append("")
    lines.extend(
        _render_detail_section(
            title="Divergences",
            details=[
                detail
                for detail in details
                if detail["comparison_status"]
                == ShadowComparisonStatus.DIVERGENCE.value
            ],
        )
    )
    lines.extend(
        _render_detail_section(
            title="Résultats non concluants",
            details=[
                detail
                for detail in details
                if detail["comparison_status"]
                == ShadowComparisonStatus.INCONCLUSIVE.value
            ],
        )
    )
    lines.extend(
        _render_detail_section(
            title="Occurrences proposées dans le manuscrit auteur",
            details=[
                detail
                for detail in details
                if detail["document_kind"] == "author"
                and detail["actions_native"]
            ],
        )
    )
    lines.extend(
        _render_detail_section(
            title="Occurrences résiduelles dans les copies corrigées",
            details=[
                detail
                for detail in details
                if detail["document_kind"] == "edited_reference"
                and detail["actions_native"]
            ],
        )
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Évalue localement deux verticales shadow orthotypographiques."
    )
    parser.add_argument("--raw-docx", required=True)
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


def _print_summary(report: dict[str, Any], output_dir: Path) -> None:
    print("Documents auteur analysés : 1")
    print(
        "Copies corrigées analysées : "
        f"{report['scope']['edited_reference_documents']}"
    )
    for rule_id in RULE_IDS:
        print()
        print(rule_id)
        for kind, label in (("author", "auteur"), ("edited_reference", "corrigé")):
            summary = report["aggregate"][kind][rule_id]
            statuses = summary["comparison_statuses"]
            print(
                "  {label} : {actions} actions proposées, {match} MATCH, "
                "{divergence} DIVERGENCE, {inconclusive} INCONCLUSIVE".format(
                    label=label,
                    actions=summary["native_actions_proposed"],
                    match=statuses[ShadowComparisonStatus.MATCH.value],
                    divergence=statuses[ShadowComparisonStatus.DIVERGENCE.value],
                    inconclusive=statuses[
                        ShadowComparisonStatus.INCONCLUSIVE.value
                    ],
                )
            )
    print()
    print(f"Rapports écrits dans : {output_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report, _json_path, _markdown_path = evaluate_corpus(
            raw_docx=args.raw_docx,
            reference_dir=args.reference_dir,
            output_dir=args.output_dir,
        )
    except EvaluationInputError as exc:
        print(f"Évaluation impossible : {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - barrière CLI défensive
        print(
            "Erreur technique pendant l’évaluation "
            f"({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1
    _print_summary(report, _resolved_path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
