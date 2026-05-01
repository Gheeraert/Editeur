from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from purh_editorial.config import AppSettings
from purh_editorial.io.docx_exporter import DocxExporter
from purh_editorial.io.importer_registry import ImporterRegistry
from purh_editorial.io.tei_xml_exporter import TeiXmlExporter
from purh_editorial.model import ModuleRun, PipelineResult, ProcessingReport
from purh_editorial.model.report import utc_now_iso
from purh_editorial.serialization import to_plain_data
from purh_editorial.services.bibliography_normalizer import BibliographyNormalizer
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.metopes_mapper import MetopesMapper
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.structure_service import StructurePreparationService
from purh_editorial.services.structure_ai_arbitrator import (
    GroqStructureAiProvider,
    StructureAiArbitrationSettings,
    StructureAiArbitrator,
    StructureAiProvider,
    settings_for_ai_aggressiveness,
)
from purh_editorial.services.ai_editorial_service import AIEditorialService
from purh_editorial.utils import make_id


@dataclass
class Step1Options:
    # Legacy flag kept for backward compatibility with existing callers.
    # It now controls only editorial AI, never structure AI arbitration.
    enable_ai: bool = False
    enable_structure_ai: bool = False
    enable_editorial_ai: bool = False
    decision_mode: str | None = None
    ai_aggressiveness: str = "conservative"
    ai_provider: str = "groq"
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_base_url: str | None = None
    max_ai_calls: int = 6               # appels Groq max (modération)
    max_structure_ai_calls: int = 6
    output_path: Path | None = None
    template_path: Path | None = None
    tei_output_path: Path | None = None

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
        if not self.decision_mode:
            return bool(self.enable_structure_ai)
        mode = self.normalized_decision_mode()
        if mode == "heuristic_ai_local":
            return True
        return False

    def editorial_ai_enabled(self) -> bool:
        if self.decision_mode:
            # Decision modes explicitly control IA families.
            return False
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
    ) -> None:
        self.settings     = settings
        self.orthotypo    = OrthotypoService()
        self.structure    = StructurePreparationService()
        self.footnotes    = FootnoteNormalizer()
        self.bibliography = BibliographyNormalizer()
        self.mapper       = MetopesMapper()
        self.ai           = AIEditorialService(
            api_key  = settings.ai.api_key,
            model    = settings.ai.model,
            base_url = settings.ai.base_url,
            timeout  = settings.ai.timeout_seconds,
        )
        if structure_ai_provider is None and settings.ai.enabled:
            structure_ai_provider = GroqStructureAiProvider(
                api_key=settings.ai.api_key or "",
                model=settings.ai.model,
                base_url=settings.ai.base_url,
                timeout=settings.ai.timeout_seconds,
            )
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

        if isinstance(self.structure_ai.provider, GroqStructureAiProvider):
            if options.ai_provider and str(options.ai_provider).lower() != "groq":
                report.warnings.append(
                    f"Unsupported ai_provider '{options.ai_provider}' for current runtime; using Groq provider."
                )
            if options.ai_api_key:
                self.structure_ai.provider.api_key = options.ai_api_key
                self.ai.api_key = options.ai_api_key
            if options.ai_base_url:
                self.structure_ai.provider.base_url = options.ai_base_url.rstrip("/")
                self.ai.base_url = options.ai_base_url.rstrip("/")
            if options.ai_model:
                self.structure_ai.provider.model = options.ai_model
                self.ai.model = options.ai_model

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
        quote_punctuation_diags = self.orthotypo.analyze_quote_punctuation(document)
        report.diagnostics.extend(quote_punctuation_diags)
        report.transformations.extend(typo_tr)
        report.add_module_run(ModuleRun(
            module_name="orthotypo",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={
                "corrections": len(typo_tr),
                "quote_punctuation_diagnostics": len(quote_punctuation_diags),
            },
        ))

        # ── 3. Reconnaissance de structure ────────────────────────────────────
        t0 = utc_now_iso()
        struct_diags, struct_tr = self.structure.process(document)
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
        ai_local_enabled = bool(options.structure_ai_enabled() and self.settings.ai.enabled)
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

        # ── 4. Normalisation des notes de bas de page ─────────────────────────
        t0 = utc_now_iso()
        document, note_tr = self.footnotes.apply(document)
        note_diags = self.footnotes.analyze_note_call_placement(document)
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
        editorial_ai_enabled = bool(options.editorial_ai_enabled() and self.settings.ai.enabled)
        if editorial_ai_enabled:
            t0 = utc_now_iso()
            document, ai_tr = self.ai.apply(document, max_calls=options.max_ai_calls)
            report.transformations.extend(ai_tr)
            ai_status = "success" if ai_tr is not None else "degraded"
            report.add_module_run(ModuleRun(
                module_name="ai_editorial",
                version=self.version,
                started_at=t0,
                finished_at=utc_now_iso(),
                status=ai_status,
                summary={
                    "corrections_applied": len(ai_tr),
                    "model": self.settings.ai.model,
                },
            ))

        # ── 7. Application des styles Métopes ─────────────────────────────────
        t0 = utc_now_iso()
        document, mapper_tr = self.mapper.apply(document)
        report.transformations.extend(mapper_tr)
        report.add_module_run(ModuleRun(
            module_name="metopes_mapper",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={"styles_assigned": len(mapper_tr)},
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

        tei_xml: str | None = None
        try:
            t0 = utc_now_iso()
            tei_xml = TeiXmlExporter().export_document(document)
            report.add_module_run(ModuleRun(
                module_name="tei_xml_export",
                version=self.version,
                started_at=t0,
                finished_at=utc_now_iso(),
                summary={"generated": tei_xml is not None},
            ))
        except Exception as exc:  # noqa: BLE001
            report.warnings.append(f"TEI export skipped: {exc}")

        if options.tei_output_path and tei_xml is not None:
            try:
                t0 = utc_now_iso()
                options.tei_output_path.parent.mkdir(parents=True, exist_ok=True)
                options.tei_output_path.write_text(tei_xml, encoding="utf-8")
                report.add_module_run(ModuleRun(
                    module_name="tei_xml_write",
                    version=self.version,
                    started_at=t0,
                    finished_at=utc_now_iso(),
                    summary={"output": str(options.tei_output_path)},
                ))
            except Exception as exc:  # noqa: BLE001
                report.warnings.append(f"TEI write skipped: {exc}")

        pivot = {
            "document": to_plain_data(document),
            "report":   to_plain_data(report),
        }
        pipeline_result = PipelineResult(
            source_document=document,
            styled_document=document,
            report=report,
            pivot_payload=pivot,
            tei_xml=tei_xml,
        )
        return Step1Result(pipeline_result=pipeline_result, output_docx=output_docx)

