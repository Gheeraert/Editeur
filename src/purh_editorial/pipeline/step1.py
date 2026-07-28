from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import tempfile

from purh_editorial.config import AppSettings
from purh_editorial.io.docx_exporter import DocxExporter
from purh_editorial.io.importer_registry import ImporterRegistry
from purh_editorial.io.tei_xml_exporter import TeiTableExportError, media_filename_for_asset
from purh_editorial.model import ModuleRun, PipelineResult, ProcessingReport
from purh_editorial.model.report import utc_now_iso
from purh_editorial.serialization import build_pivot_payload, pivot_to_json
from purh_editorial.services.bibliography_normalizer import BibliographyNormalizer
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.metopes_mapper import MetopesMapper
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.pivot_canonicalizer import PivotCanonicalizer
from purh_editorial.services.pivot_export_gate import PivotValidationError, export_tei_for_production
from purh_editorial.services.pivot_validator import PivotValidator
from purh_editorial.services.structure_service import StructurePreparationService
from purh_editorial.services.structure_service import settings_for_heuristic_profile
from purh_editorial.services.word_review_service import (
    WordReviewError,
    WordReviewResult,
    WordReviewService,
)
from purh_editorial.services.structure_ai_arbitrator import (
    AnthropicStructureAiProvider,
    GroqStructureAiProvider,
    StructureAiArbitrationSettings,
    StructureAiArbitrator,
    StructureAiProvider,
    settings_for_ai_aggressiveness,
)
from purh_editorial.services.ai_editorial_service import AIEditorialService
from purh_editorial.utils import make_id


def _invalidate_tei_output(path: Path | None, report: ProcessingReport) -> None:
    """Remove a stale TEI target after the current production export failed."""
    if path is None or not path.exists():
        return
    try:
        path.unlink()
    except OSError as exc:
        report.errors.append(f"TEI stale output cleanup failed ({type(exc).__name__}): {exc}")


def _write_tei_xml_atomically(path: Path, xml: str) -> None:
    """Write a TEI file beside its target, then replace the target atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
        )
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(xml)
        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                raise OSError(
                    f"{exc}; temporary TEI cleanup failed: {cleanup_exc}"
                ) from exc
        raise


@dataclass
class Step1Options:
    # Legacy flag kept for backward compatibility with existing callers.
    # It now controls only editorial AI, never structure AI arbitration.
    enable_ai: bool = False
    enable_structure_ai: bool = False
    enable_editorial_ai: bool = False
    decision_mode: str | None = None
    ai_aggressiveness: str = "conservative"
    # ── IA structurelle (arbitrage zones grises) ──────────────────────────
    ai_provider: str = "groq"
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_base_url: str | None = None
    max_structure_ai_calls: int = 6

    # ── IA éditoriale (corrections orthotypo) — provider optionnellement distinct
    # Si vides, on hérite des champs ai_* de l'IA structurelle.
    editorial_ai_provider: str = ""
    editorial_ai_api_key: str | None = None
    editorial_ai_model: str | None = None
    editorial_ai_base_url: str | None = None
    max_ai_calls: int = 6
    apply_metopes_styles: bool = False
    heuristic_profile: str = "conservative"
    heading_transform_threshold: float | None = None
    heading_diagnostic_threshold: float | None = None
    poetry_transform_threshold: float | None = None
    poetry_diagnostic_threshold: float | None = None
    output_path: Path | None = None
    word_review_output_path: Path | None = None
    template_path: Path | None = None
    tei_output_path: Path | None = None
    pivot_json_output_path: Path | None = None

    _ALLOWED_DECISION_MODES = {
        "deterministic",
        "heuristic",
        "heuristic_ai_local",
        "ai_exploratory",
    }

    def normalized_decision_mode(self) -> str:
        if not self.decision_mode:
            return "heuristic"
        mode = str(self.decision_mode).strip().lower()
        if mode in self._ALLOWED_DECISION_MODES:
            return mode
        return "heuristic"

    def structure_ai_enabled(self) -> bool:
        if self.decision_mode:
            mode = self.normalized_decision_mode()
            if mode in {"deterministic", "ai_exploratory"}:
                return False
            if mode == "heuristic_ai_local":
                return True
        return bool(self.enable_structure_ai)

    def editorial_ai_enabled(self) -> bool:
        if self.decision_mode:
            mode = self.normalized_decision_mode()
            if mode in {"deterministic", "ai_exploratory"}:
                return False
            # In heuristic modes, explicit checkbox controls editorial AI.
            return bool(self.enable_editorial_ai)
        if self.enable_editorial_ai:
            return True
        # Backward-compatibility: legacy flag enables editorial AI only.
        return bool(self.enable_ai)

    def exploratory_mode_requested(self) -> bool:
        return bool(self.decision_mode and self.normalized_decision_mode() == "ai_exploratory")

@dataclass
class Step1Result:
    pipeline_result: PipelineResult
    output_docx: Path | None = None
    word_review_result: WordReviewResult | None = None


class Step1Pipeline:
    """
    Étape 1 — Préparation éditoriale d'un manuscrit auteur.

    Passe 1 (déterministe) :
      orthotypo → structure → notes → bibliographie → styles Métopes

    Passe 2 (IA, optionnelle) :
      corrections IA ciblées (2-12 mots, Groq llama-3.3-70b, max MAX_AI_CALLS appels)

    Surlignages :
      jaune   → orthotypographie
      vert    → notes de bas de page
      turquoise → bibliographie
      rose    → suggestions IA appliquées
    """

    version = "2.0.0"

    def __init__(
        self,
        settings: AppSettings,
        *,
        structure_ai_provider: StructureAiProvider | None = None,
        word_review_service: WordReviewService | None = None,
    ) -> None:
        self.settings     = settings
        self.orthotypo    = OrthotypoService()
        self.structure    = StructurePreparationService()
        self.footnotes    = FootnoteNormalizer()
        self.bibliography = BibliographyNormalizer()
        self.pivot_canonicalizer = PivotCanonicalizer()
        self.pivot_validator = PivotValidator()
        self.mapper       = MetopesMapper()
        self.word_review = word_review_service or WordReviewService()
        self.ai           = AIEditorialService(
            api_key  = settings.ai.api_key,
            model    = settings.ai.model,
            base_url = settings.ai.base_url,
            timeout  = settings.ai.timeout_seconds,
        )
        if structure_ai_provider is None and settings.ai.enabled:
            structure_ai_provider = _make_structure_provider(settings)
        self.structure_ai = StructureAiArbitrator(
            provider=structure_ai_provider,
            settings=StructureAiArbitrationSettings(model=settings.ai.model),
        )

    def run(self, source_path: Path, options: Step1Options | None = None) -> Step1Result:
        options = options or Step1Options()
        report  = ProcessingReport(
            report_id=make_id("report"),
            document_id="",
        )

        if options.exploratory_mode_requested():
            report.warnings.append(
                "Decision mode 'ai_exploratory' is not implemented yet; falling back to heuristic mode without AI."
            )

        heuristics_enabled = options.normalized_decision_mode() != "deterministic"
        structure_settings, structure_setting_warnings = settings_for_heuristic_profile(
            options.heuristic_profile,
            heading_transform_threshold=options.heading_transform_threshold,
            heading_diagnostic_threshold=options.heading_diagnostic_threshold,
            poetry_transform_threshold=options.poetry_transform_threshold,
            poetry_diagnostic_threshold=options.poetry_diagnostic_threshold,
            enable_scored_heuristics=heuristics_enabled,
        )
        report.warnings.extend(structure_setting_warnings)
        self.structure.heuristic_settings = structure_settings

        structure_ai_requested = bool(options.structure_ai_enabled())
        requested_provider = str(options.ai_provider or "groq").strip().lower()
        _SUPPORTED_PROVIDERS = {"groq", "anthropic"}
        if (
            structure_ai_requested
            and self.structure_ai.provider is None
            and options.ai_api_key
        ):
            if requested_provider not in _SUPPORTED_PROVIDERS:
                report.warnings.append(
                    f"Unsupported ai_provider '{options.ai_provider}' for current runtime; "
                    "structure AI provider not created."
                )
            else:
                self.structure_ai.provider = _make_structure_provider_from_options(
                    options, self.settings
                )
                self.ai.api_key = options.ai_api_key

        # Propagate session-level overrides to the active provider.
        if isinstance(self.structure_ai.provider, GroqStructureAiProvider):
            if options.ai_api_key:
                self.structure_ai.provider.api_key = options.ai_api_key
                self.ai.api_key = options.ai_api_key
            if options.ai_base_url:
                self.structure_ai.provider.base_url = options.ai_base_url.rstrip("/")
                self.ai.base_url = options.ai_base_url.rstrip("/")
            if options.ai_model:
                self.structure_ai.provider.model = options.ai_model
                self.ai.model = options.ai_model
        elif isinstance(self.structure_ai.provider, AnthropicStructureAiProvider):
            if options.ai_api_key:
                self.structure_ai.provider.api_key = options.ai_api_key
            if options.ai_model:
                self.structure_ai.provider.model = options.ai_model

        # ── Configuration IA éditoriale (provider potentiellement distinct) ───
        # Les champs editorial_ai_* surchargent les champs ai_* quand renseignés.
        edi_provider = (options.editorial_ai_provider or str(options.ai_provider or "groq")).strip().lower()
        # API key fallback must follow the effective editorial provider selected
        # for this session (not the global provider in settings).
        if options.editorial_ai_api_key:
            edi_key = options.editorial_ai_api_key
        elif options.ai_api_key:
            edi_key = options.ai_api_key
        elif edi_provider == "anthropic":
            edi_key = self.settings.ai.anthropic_api_key
        else:
            edi_key = self.settings.ai.api_key
        if edi_provider == "anthropic":
            edi_model = (
                options.editorial_ai_model
                or options.ai_model
                or self.settings.ai.anthropic_model
            )
            edi_base_url = (
                options.editorial_ai_base_url
                or options.ai_base_url
                or self.settings.ai.anthropic_base_url
            )
        else:
            edi_model = options.editorial_ai_model or options.ai_model or self.settings.ai.model
            edi_base_url = (
                options.editorial_ai_base_url
                or options.ai_base_url
                or self.settings.ai.base_url
            )
        self.ai.provider = edi_provider
        if edi_key:
            self.ai.api_key = edi_key
        if edi_model:
            self.ai.model = edi_model
        if edi_base_url:
            self.ai.base_url = edi_base_url.rstrip("/")

        # ── 1. Ingestion ──────────────────────────────────────────────────────
        t0 = utc_now_iso()
        registry = ImporterRegistry()
        document = registry.load_document(source_path)
        report.document_id = document.document_id
        report.add_module_run(ModuleRun(
            module_name="ingestion",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={"blocks": len(document.blocks), "notes": len(document.notes)},
        ))

        # ── 2. Orthotypographie (déterministe) ────────────────────────────────
        t0 = utc_now_iso()
        document, typo_tr = self.orthotypo.apply(document)
        unvalidated_typo_diags = self.orthotypo.analyze_unvalidated_rules(document)
        quote_punctuation_diags = self.orthotypo.analyze_quote_punctuation(document)
        incise_dash_diags = self.orthotypo.analyze_incise_dash(document)
        report.diagnostics.extend(quote_punctuation_diags)
        report.diagnostics.extend(unvalidated_typo_diags)
        report.diagnostics.extend(incise_dash_diags)
        report.transformations.extend(typo_tr)
        report.add_module_run(ModuleRun(
            module_name="orthotypo",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={
                "corrections": len(typo_tr),
                "unvalidated_rule_diagnostics": len(unvalidated_typo_diags),
                "quote_punctuation_diagnostics": len(quote_punctuation_diags),
                "incise_dash_diagnostics": len(incise_dash_diags),
            },
        ))

        # ── 3. Reconnaissance de structure ────────────────────────────────────
        t0 = utc_now_iso()
        structure_mode = "deterministic" if options.normalized_decision_mode() == "deterministic" else "heuristic"
        struct_diags, struct_tr = self.structure.process(document, mode=structure_mode)
        report.diagnostics.extend(struct_diags)
        report.transformations.extend(struct_tr)
        report.add_module_run(ModuleRun(
            module_name="structure",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={
                "annotations": len(struct_tr),
                "bibliography_items": len(document.bibliography),
                "structure_mode": structure_mode,
                "heuristic_profile": options.heuristic_profile,
                "heuristics_enabled": heuristics_enabled,
                "heading_transform_threshold": structure_settings.heading_transform_threshold,
                "heading_diagnostic_threshold": structure_settings.heading_diagnostic_threshold,
                "heading_ai_min_score": structure_settings.heading_ai_min_score,
                "heading_ai_max_score": structure_settings.heading_ai_max_score,
                "poetry_transform_threshold": structure_settings.poetry_transform_threshold,
                "poetry_diagnostic_threshold": structure_settings.poetry_diagnostic_threshold,
                "poetry_ai_min_score": structure_settings.poetry_ai_min_score,
                "poetry_ai_max_score": structure_settings.poetry_ai_max_score,
            },
        ))

        # ── 3b. Arbitrage IA local des zones grises structurelles ────────────
        t0 = utc_now_iso()
        structure_ai_settings, structure_ai_calls_cap = settings_for_ai_aggressiveness(
            options.ai_aggressiveness,
            base_model=options.ai_model or self.settings.ai.model,
            base_max_structure_ai_calls=options.max_structure_ai_calls,
        )
        self.structure_ai.settings = structure_ai_settings
        ai_local_enabled = bool(structure_ai_requested)
        local_diags, local_warnings, ai_calls = self.structure_ai.arbitrate_from_diagnostics(
            document=document,
            diagnostics=struct_diags,
            enable_ai=ai_local_enabled,
            max_calls=structure_ai_calls_cap,
        )
        report.diagnostics.extend(local_diags)
        report.warnings.extend(local_warnings)
        report.add_module_run(ModuleRun(
            module_name="structure_ai_arbitration",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            status="success",
            summary={
                "enabled": ai_local_enabled,
                "decision_mode": options.normalized_decision_mode(),
                "ai_aggressiveness": options.ai_aggressiveness,
                "ai_calls": ai_calls,
                "max_structure_ai_calls": structure_ai_calls_cap,
                "confidence_threshold": structure_ai_settings.confidence_threshold,
                "diagnostics": len(local_diags),
            },
        ))

        # ── 3c. Analyse IA des clusters de paragraphes courts ────────────────
        t0 = utc_now_iso()
        cluster_diags, cluster_warnings, cluster_calls = self.structure_ai.analyze_short_paragraph_clusters(
            document=document,
            enable_ai=ai_local_enabled,
            max_calls=max(0, structure_ai_calls_cap - ai_calls),
        )
        report.diagnostics.extend(cluster_diags)
        report.warnings.extend(cluster_warnings)
        report.add_module_run(ModuleRun(
            module_name="structure_ai_clusters",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            status="success",
            summary={
                "enabled": ai_local_enabled,
                "ai_calls": cluster_calls,
                "cluster_diagnostics": len(cluster_diags),
            },
        ))

        # ── 3d. Application IA structurelle (clusters) ──────────────────────
        t0 = utc_now_iso()
        cluster_tr, cluster_apply_diags, cluster_apply_summary = self.structure_ai.apply_cluster_transformations(
            document=document,
            diagnostics=cluster_diags,
            enable_ai_transform=ai_local_enabled,
            confidence_threshold=structure_ai_settings.confidence_threshold,
        )
        report.transformations.extend(cluster_tr)
        report.diagnostics.extend(cluster_apply_diags)
        provider_obj = self.structure_ai.provider
        provider_name = type(provider_obj).__name__ if provider_obj is not None else None
        provider_model = getattr(provider_obj, "model", None) if provider_obj is not None else None
        report.add_module_run(ModuleRun(
            module_name="structure_ai_apply",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            status="success",
            summary={
                "enabled": ai_local_enabled,
                "provider": provider_name,
                "model": provider_model,
                "confidence_threshold": structure_ai_settings.confidence_threshold,
                "candidates": int(cluster_apply_summary.get("candidates", 0)),
                "applied": int(cluster_apply_summary.get("applied", 0)),
                "refused": int(cluster_apply_summary.get("refused", 0)),
                "refusal_reasons": cluster_apply_summary.get("refusal_reasons", {}),
            },
        ))

        # ── 4. Normalisation des notes de bas de page ─────────────────────────
        t0 = utc_now_iso()
        document, note_tr = self.footnotes.apply(document)
        note_diags = self.footnotes.analyze_note_call_placement(document)
        note_diags.extend(self.footnotes.analyze_note_normalization_exclusions(document))
        report.diagnostics.extend(note_diags)
        report.transformations.extend(note_tr)
        report.add_module_run(ModuleRun(
            module_name="footnotes",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={
                "corrections": len(note_tr),
                "note_call_diagnostics": len(note_diags),
            },
        ))

        # ── 5. Normalisation bibliographique ──────────────────────────────────
        t0 = utc_now_iso()
        document, bib_tr = self.bibliography.apply(document)
        report.transformations.extend(bib_tr)
        report.add_module_run(ModuleRun(
            module_name="bibliography",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={"corrections": len(bib_tr)},
        ))

        # ── 6. Corrections IA ciblées (optionnelles) ──────────────────────────
        editorial_ai_requested = bool(options.editorial_ai_enabled())
        editorial_ai_available = bool(self.ai.available)
        editorial_ai_enabled = bool(editorial_ai_requested and editorial_ai_available)
        if editorial_ai_requested:
            t0 = utc_now_iso()
            if editorial_ai_enabled:
                document, ai_suggestions = self.ai.apply(document, max_calls=options.max_ai_calls)
                report.suggestions.extend(ai_suggestions)
                ai_status = "success"
            else:
                ai_suggestions = []
                ai_status = "skipped"
                report.warnings.append("Editorial AI skipped: no API key configured for selected provider.")
            report.add_module_run(ModuleRun(
                module_name="ai_editorial",
                version=self.version,
                started_at=t0,
                finished_at=utc_now_iso(),
                status=ai_status,
                summary={
                    "editorial_ai_requested": editorial_ai_requested,
                    "editorial_ai_available": editorial_ai_available,
                    "editorial_ai_enabled": editorial_ai_enabled,
                    "enabled": editorial_ai_enabled,
                    "suggestions_produced": len(ai_suggestions),
                    "provider": self.ai.provider,
                    "model": self.ai.model,
                    "base_url": self.ai.base_url,
                    "max_ai_calls": options.max_ai_calls,
                },
            ))

        # ── 7. Application des styles Métopes ─────────────────────────────────
        t0 = utc_now_iso()
        canonicalization_tr = self.pivot_canonicalizer.apply(document)
        report.transformations.extend(canonicalization_tr)
        report.add_module_run(ModuleRun(
            module_name="pivot_canonicalizer",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={"semantic_updates": len(canonicalization_tr)},
        ))

        t0 = utc_now_iso()
        pivot_diagnostics = self.pivot_validator.validate(document)
        report.diagnostics.extend(pivot_diagnostics)
        report.add_module_run(ModuleRun(
            module_name="pivot_validator",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={
                "diagnostics": len(pivot_diagnostics),
                "errors": sum(1 for diag in pivot_diagnostics if diag.severity == "error"),
                "warnings": sum(1 for diag in pivot_diagnostics if diag.severity == "warning"),
            },
        ))

        t0 = utc_now_iso()
        mapper_tr = []
        mapper_status = "skipped"
        if options.apply_metopes_styles:
            document, mapper_tr = self.mapper.apply(document)
            report.transformations.extend(mapper_tr)
            mapper_status = "success"
        report.add_module_run(ModuleRun(
            module_name="metopes_mapper",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            status=mapper_status,
            summary={"enabled": options.apply_metopes_styles, "styles_assigned": len(mapper_tr)},
        ))

        # ── 8. Export DOCX ─────────────────────────────────────────────────────
        output_docx: Path | None = None
        if options.output_path:
            t0 = utc_now_iso()
            exporter = DocxExporter(template_path=options.template_path)
            output_docx = exporter.export(document, options.output_path)
            report.add_module_run(ModuleRun(
                module_name="docx_export",
                version=self.version,
                started_at=t0,
                finished_at=utc_now_iso(),
                summary={"output": str(output_docx)},
            ))

        word_review_result: WordReviewResult | None = None
        if options.word_review_output_path is not None:
            t0 = utc_now_iso()
            if output_docx is None:
                message = (
                    "Document de revision Word non produit : aucun DOCX candidat n'a ete demande."
                )
                report.errors.append(message)
                report.add_module_run(ModuleRun(
                    module_name="word_review",
                    version=self.version,
                    started_at=t0,
                    finished_at=utc_now_iso(),
                    status="failed",
                    summary={
                        "original": str(source_path),
                        "candidate": None,
                        "output": str(options.word_review_output_path),
                        "error": message,
                    },
                ))
            else:
                try:
                    word_review_result = self.word_review.create_review_document(
                        original_path=source_path,
                        revised_path=output_docx,
                        output_path=options.word_review_output_path,
                    )
                    report.add_module_run(ModuleRun(
                        module_name="word_review",
                        version=self.version,
                        started_at=t0,
                        finished_at=utc_now_iso(),
                        status="success",
                        summary={
                            "original": str(source_path),
                            "candidate": str(output_docx),
                            "output": str(word_review_result.output_path),
                            "has_tracked_changes": word_review_result.has_tracked_changes,
                        },
                    ))
                except WordReviewError as exc:
                    report.errors.append(f"Word review failed ({type(exc).__name__}): {exc}")
                    report.add_module_run(ModuleRun(
                        module_name="word_review",
                        version=self.version,
                        started_at=t0,
                        finished_at=utc_now_iso(),
                        status="failed",
                        summary={
                            "original": str(source_path),
                            "candidate": str(output_docx),
                            "output": str(options.word_review_output_path),
                            "error": str(exc),
                        },
                    ))

        tei_xml: str | None = None
        try:
            t0 = utc_now_iso()
            tei_xml, gate_diagnostics = export_tei_for_production(
                document,
                fail_on_pivot_error=True,
                run_canonicalization=False,
            )
            report.add_module_run(ModuleRun(
                module_name="tei_xml_export",
                version=self.version,
                started_at=t0,
                finished_at=utc_now_iso(),
                summary={
                    "generated": tei_xml is not None,
                    "pivot_errors": sum(1 for diag in gate_diagnostics if diag.severity == "error"),
                },
            ))
        except PivotValidationError as exc:
            _invalidate_tei_output(options.tei_output_path, report)
            report.warnings.append(f"TEI export blocked: {exc}")
            report.diagnostics.extend(exc.diagnostics)
        except TeiTableExportError as exc:
            _invalidate_tei_output(options.tei_output_path, report)
            report.errors.append(str(exc))
            report.add_module_run(ModuleRun(
                module_name="tei_xml_export",
                version=self.version,
                started_at=t0,
                finished_at=utc_now_iso(),
                status="failed",
                summary={
                    "generated": False,
                    "table_failures": sum(
                        item.get("code") != "table_exported_to_tei"
                        for item in exc.diagnostics
                    ),
                    "table_diagnostics": exc.diagnostics,
                },
            ))
        except Exception as exc:  # noqa: BLE001
            _invalidate_tei_output(options.tei_output_path, report)
            report.warnings.append(f"TEI export skipped ({type(exc).__name__}): {exc}")

        if options.tei_output_path and tei_xml is not None:
            try:
                t0 = utc_now_iso()
                _write_tei_xml_atomically(options.tei_output_path, tei_xml)
                media_written = 0
                if document.image_assets:
                    media_dir = options.tei_output_path.parent / "media"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    for asset in document.image_assets.values():
                        (media_dir / media_filename_for_asset(asset)).write_bytes(asset.data)
                        media_written += 1
                report.add_module_run(ModuleRun(
                    module_name="tei_xml_write",
                    version=self.version,
                    started_at=t0,
                    finished_at=utc_now_iso(),
                    summary={"output": str(options.tei_output_path), "media_written": media_written},
                ))
            except Exception as exc:  # noqa: BLE001
                report.warnings.append(f"TEI write skipped ({type(exc).__name__}): {exc}")

        if options.pivot_json_output_path is not None:
            pivot_json_module_run: ModuleRun | None = None
            try:
                t0 = utc_now_iso()
                options.pivot_json_output_path.parent.mkdir(parents=True, exist_ok=True)
                pivot_json_module_run = ModuleRun(
                    module_name="pivot_json_write",
                    version=self.version,
                    started_at=t0,
                    finished_at=utc_now_iso(),
                    status="success",
                    summary={"output": str(options.pivot_json_output_path)},
                )
                report.add_module_run(pivot_json_module_run)
                pivot_json_text = pivot_to_json(document, report=report)
                options.pivot_json_output_path.write_text(pivot_json_text, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                if pivot_json_module_run is not None and report.module_runs and report.module_runs[-1] is pivot_json_module_run:
                    report.module_runs.pop()
                report.warnings.append(f"Pivot JSON write skipped ({type(exc).__name__}): {exc}")

        pivot = build_pivot_payload(document, report=report)
        pipeline_result = PipelineResult(
            source_document=document,
            styled_document=document,
            report=report,
            pivot_payload=pivot,
            tei_xml=tei_xml,
        )
        return Step1Result(
            pipeline_result=pipeline_result,
            output_docx=output_docx,
            word_review_result=word_review_result,
        )


# ── Factories de providers IA ─────────────────────────────────────────────────

def _make_structure_provider(settings: "AppSettings") -> StructureAiProvider:
    """Crée le provider structurel selon PURH_AI_PROVIDER."""
    if settings.ai.provider == "anthropic":
        return AnthropicStructureAiProvider(
            api_key=settings.ai.anthropic_api_key or "",
            model=settings.ai.anthropic_model,
            base_url=settings.ai.anthropic_base_url,
            timeout=settings.ai.timeout_seconds,
        )
    return GroqStructureAiProvider(
        api_key=settings.ai.api_key or "",
        model=settings.ai.model,
        base_url=settings.ai.base_url,
        timeout=settings.ai.timeout_seconds,
    )


def _make_structure_provider_from_options(
    options: "Step1Options",
    settings: "AppSettings",
) -> StructureAiProvider:
    """Crée le provider structurel depuis les options de session (UI)."""
    requested = str(options.ai_provider or "groq").strip().lower()
    if requested == "anthropic":
        return AnthropicStructureAiProvider(
            api_key=options.ai_api_key or settings.ai.anthropic_api_key or "",
            model=options.ai_model or settings.ai.anthropic_model,
            base_url=options.ai_base_url or settings.ai.anthropic_base_url,
            timeout=settings.ai.timeout_seconds,
        )
    return GroqStructureAiProvider(
        api_key=options.ai_api_key or settings.ai.api_key or "",
        model=options.ai_model or settings.ai.model,
        base_url=options.ai_base_url or settings.ai.base_url,
        timeout=settings.ai.timeout_seconds,
    )
