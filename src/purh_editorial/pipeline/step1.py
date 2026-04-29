from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from purh_editorial.config import AppSettings
from purh_editorial.io.docx_exporter import DocxExporter
from purh_editorial.io.importer_registry import ImporterRegistry
from purh_editorial.model import ModuleRun, PipelineResult, ProcessingReport
from purh_editorial.model.report import utc_now_iso
from purh_editorial.serialization import to_plain_data
from purh_editorial.services.bibliography_normalizer import BibliographyNormalizer
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.metopes_mapper import MetopesMapper
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.structure_service import StructurePreparationService
from purh_editorial.services.ai_editorial_service import AIEditorialService
from purh_editorial.utils import make_id


@dataclass
class Step1Options:
    enable_ai: bool = True
    max_ai_calls: int = 6               # appels Groq max (modération)
    output_path: Path | None = None
    template_path: Path | None = None


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

    def __init__(self, settings: AppSettings) -> None:
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

    def run(self, source_path: Path, options: Step1Options | None = None) -> Step1Result:
        options = options or Step1Options()
        report  = ProcessingReport(
            report_id=make_id("report"),
            document_id="",
        )

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
        report.transformations.extend(typo_tr)
        report.add_module_run(ModuleRun(
            module_name="orthotypo",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={"corrections": len(typo_tr)},
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

        # ── 4. Normalisation des notes de bas de page ─────────────────────────
        t0 = utc_now_iso()
        document, note_tr = self.footnotes.apply(document)
        report.transformations.extend(note_tr)
        report.add_module_run(ModuleRun(
            module_name="footnotes",
            version=self.version,
            started_at=t0,
            finished_at=utc_now_iso(),
            summary={"corrections": len(note_tr)},
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
        if options.enable_ai and self.settings.ai.enabled:
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

        # ── 8. Export DOCX ────────────────────────────────────────────────────
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

        pivot = {
            "document": to_plain_data(document),
            "report":   to_plain_data(report),
        }
        pipeline_result = PipelineResult(
            source_document=document,
            styled_document=document,
            report=report,
            pivot_payload=pivot,
        )
        return Step1Result(pipeline_result=pipeline_result, output_docx=output_docx)
