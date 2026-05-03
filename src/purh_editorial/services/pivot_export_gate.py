from __future__ import annotations

from dataclasses import dataclass

from purh_editorial.io.tei_xml_exporter import TeiXmlExporter
from purh_editorial.model import Diagnostic, Document
from purh_editorial.services.pivot_canonicalizer import PivotCanonicalizer
from purh_editorial.services.pivot_validator import PivotValidator


@dataclass(slots=True)
class PivotValidationError(Exception):
    message: str
    diagnostics: list[Diagnostic]
    document_id: str

    def __str__(self) -> str:
        return self.message


def export_tei_for_production(
    document: Document,
    *,
    fail_on_pivot_error: bool = True,
    run_canonicalization: bool = True,
) -> tuple[str | None, list[Diagnostic]]:
    # Exporters are renderers only. Production export must pass pivot validation.
    if run_canonicalization:
        PivotCanonicalizer().apply(document)

    diagnostics = PivotValidator().validate(document)
    error_diagnostics = [diag for diag in diagnostics if diag.severity == "error"]
    if fail_on_pivot_error and error_diagnostics:
        raise PivotValidationError(
            message="Pivot validation failed; production TEI export blocked.",
            diagnostics=error_diagnostics,
            document_id=document.document_id,
        )

    return TeiXmlExporter().export_document(document), diagnostics
