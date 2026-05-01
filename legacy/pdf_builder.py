from __future__ import annotations

"""Orchestrateur PDF pour la chaîne Impressions.

Ce module relie les trois étages déjà posés :

1. TEI normalisé -> modèle sémantique
2. modèle sémantique -> LaTeX
3. LaTeX -> PDF via LuaLaTeX

La V1 vise un pipeline simple, robuste et pédagogique.
Elle privilégie :
- la lisibilité du code ;
- la traçabilité du build ;
- un rapport clair ;
- des erreurs explicites.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import traceback

from .latex_renderer import LatexRenderOptions, LatexRenderer
from .semantic_model import Book, Division, FigureBlock, ListBlock, QuoteBlock, Section, VerseBlock
from .tei_to_model import parse_normalized_tei


# ---------------------------------------------------------------------------
# Résultats et statistiques
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PdfBuildStats:
    """Statistiques utiles pour le rapport de build."""

    divisions: int = 0
    sections: int = 0
    figures: int = 0
    notes: int = 0


@dataclass(slots=True)
class PdfBuildResult:
    """Résultat complet d'un build PDF."""

    success: bool
    xml_path: Path
    output_dir: Path
    tex_path: Path
    pdf_path: Path
    log_path: Path
    report_path: Path
    started_at: datetime
    finished_at: datetime
    stats: PdfBuildStats = field(default_factory=PdfBuildStats)
    warnings: list[str] = field(default_factory=list)
    commands: list[list[str]] = field(default_factory=list)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Builder principal
# ---------------------------------------------------------------------------


class PdfBuilder:
    """Pipeline complet de génération PDF à partir du TEI normalisé."""

    def __init__(
        self,
        *,
        latex_renderer: LatexRenderer | None = None,
        latex_options: LatexRenderOptions | None = None,
        latex_engine: str = "lualatex",
        compile_pdf: bool = True,
        latex_runs: int = 2,
        timeout_seconds: int = 120,
    ) -> None:
        self.renderer = latex_renderer or LatexRenderer(options=latex_options)
        self.latex_engine = latex_engine
        self.compile_pdf = compile_pdf
        self.latex_runs = max(1, latex_runs)
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def build_from_normalized_tei(self, xml_path: str | Path, output_dir: str | Path) -> PdfBuildResult:
        """Construit un PDF à partir d'un ``book.normalized.xml``.

        Étapes :
        1. lecture du TEI normalisé ;
        2. conversion en modèle sémantique ;
        3. normalisation des chemins d'images ;
        4. rendu LaTeX ;
        5. compilation PDF ;
        6. génération d'un rapport.
        """

        xml_path = Path(xml_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now()
        tex_path = output_dir / "book.tex"
        pdf_path = output_dir / "book.pdf"
        log_path = output_dir / "latex_build.log"
        report_path = output_dir / "pdf_build_report.txt"

        warnings: list[str] = []
        commands: list[list[str]] = []
        stats = PdfBuildStats()
        success = False
        error_message: str | None = None

        try:
            book = parse_normalized_tei(xml_path)
            self._absolutize_figure_paths(book, base_dir=xml_path.parent, warnings=warnings)
            stats = self._collect_stats(book)

            self.renderer.write_book(book, tex_path)

            if self.compile_pdf:
                success = self._compile_latex(
                    tex_path=tex_path,
                    output_dir=output_dir,
                    pdf_path=pdf_path,
                    log_path=log_path,
                    commands=commands,
                )
            else:
                success = tex_path.exists()
                log_path.write_text(
                    "Compilation PDF désactivée. Seul le fichier LaTeX a été généré.\n",
                    encoding="utf-8",
                )

        except Exception as exc:  # pragma: no cover - utile en production
            error_message = f"{type(exc).__name__}: {exc}"
            tb = traceback.format_exc()
            log_path.write_text(tb, encoding="utf-8")
            success = False

        finished_at = datetime.now()

        result = PdfBuildResult(
            success=success,
            xml_path=xml_path,
            output_dir=output_dir,
            tex_path=tex_path,
            pdf_path=pdf_path,
            log_path=log_path,
            report_path=report_path,
            started_at=started_at,
            finished_at=finished_at,
            stats=stats,
            warnings=warnings,
            commands=commands,
            error_message=error_message,
        )

        self._write_report(result)
        return result


# ---------------------------------------------------------------------------
# Compilation LaTeX
# ---------------------------------------------------------------------------

    def _compile_latex(
        self,
        *,
        tex_path: Path,
        output_dir: Path,
        pdf_path: Path,
        log_path: Path,
        commands: list[list[str]],
    ) -> bool:
        """Compile le fichier LaTeX avec LuaLaTeX.

        La V1 n'utilise pas biber : les bibliographies sont déjà formulées dans
        le XML et rendues comme texte.
        """

        engine_path = shutil.which(self.latex_engine)
        if engine_path is None:
            raise RuntimeError(
                f"Moteur LaTeX introuvable : '{self.latex_engine}'. "
                "Installez LuaLaTeX ou indiquez un chemin valide."
            )

        log_path.write_text("", encoding="utf-8")

        for run_index in range(1, self.latex_runs + 1):
            command = [
                engine_path,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-output-directory={output_dir.as_posix()}",
                tex_path.as_posix(),
            ]
            commands.append(command)

            process = subprocess.run(
                command,
                cwd=output_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )

            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"=== Run {run_index}/{self.latex_runs} ===\n")
                handle.write("Command: " + " ".join(command) + "\n\n")
                if process.stdout:
                    handle.write(process.stdout)
                    if not process.stdout.endswith("\n"):
                        handle.write("\n")
                if process.stderr:
                    handle.write("\n--- STDERR ---\n")
                    handle.write(process.stderr)
                    if not process.stderr.endswith("\n"):
                        handle.write("\n")
                handle.write("\n")

            if process.returncode != 0:
                return False

        return pdf_path.exists()


# ---------------------------------------------------------------------------
# Normalisation des chemins d'images
# ---------------------------------------------------------------------------

    def _absolutize_figure_paths(self, book: Book, *, base_dir: Path, warnings: list[str]) -> None:
        """Convertit en place les chemins d'images en chemins absolus.

        Pourquoi le faire ici ?
        - pour permettre au compilateur LaTeX de travailler depuis n'importe
          quel dossier de sortie ;
        - pour éviter que les figures dépendent du répertoire courant.
        """

        for division in book.front_divisions:
            self._absolutize_division_paths(division, base_dir=base_dir, warnings=warnings)
        for division in book.body_divisions:
            self._absolutize_division_paths(division, base_dir=base_dir, warnings=warnings)
        for division in book.back_divisions:
            self._absolutize_division_paths(division, base_dir=base_dir, warnings=warnings)

    def _absolutize_division_paths(self, division: Division, *, base_dir: Path, warnings: list[str]) -> None:
        self._absolutize_blocks_paths(division.blocks, base_dir=base_dir, warnings=warnings)
        for section in division.sections:
            self._absolutize_section_paths(section, base_dir=base_dir, warnings=warnings)

    def _absolutize_section_paths(self, section: Section, *, base_dir: Path, warnings: list[str]) -> None:
        self._absolutize_blocks_paths(section.blocks, base_dir=base_dir, warnings=warnings)
        for child in section.sections:
            self._absolutize_section_paths(child, base_dir=base_dir, warnings=warnings)

    def _absolutize_blocks_paths(self, blocks, *, base_dir: Path, warnings: list[str]) -> None:
        for block in blocks:
            if isinstance(block, FigureBlock):
                if block.image_path:
                    resolved = self._resolve_asset_path(block.image_path, base_dir)
                    block.image_path = resolved.as_posix()
                    if not resolved.exists():
                        warnings.append(f"Image introuvable : {resolved}")
                else:
                    warnings.append("Figure sans chemin d'image renseigné.")

                if block.alt_image_path:
                    resolved_alt = self._resolve_asset_path(block.alt_image_path, base_dir)
                    block.alt_image_path = resolved_alt.as_posix()
                    if not resolved_alt.exists():
                        warnings.append(f"Image alternative introuvable : {resolved_alt}")

            elif isinstance(block, QuoteBlock):
                self._absolutize_blocks_paths(block.blocks, base_dir=base_dir, warnings=warnings)

            elif isinstance(block, ListBlock):
                for item in block.items:
                    self._absolutize_blocks_paths(item.blocks, base_dir=base_dir, warnings=warnings)

            elif isinstance(block, VerseBlock):
                # Rien à faire pour l'instant.
                continue

    def _resolve_asset_path(self, raw_path: str, base_dir: Path) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path.resolve()
        return (base_dir / path).resolve()


# ---------------------------------------------------------------------------
# Statistiques et rapport
# ---------------------------------------------------------------------------

    def _collect_stats(self, book: Book) -> PdfBuildStats:
        stats = PdfBuildStats()
        all_divisions = [*book.front_divisions, *book.body_divisions, *book.back_divisions]
        stats.divisions = len(all_divisions)

        for division in all_divisions:
            stats.notes += len(division.notes)
            stats.sections += self._count_sections(division.sections)
            stats.figures += self._count_figures_in_division(division)

        return stats

    def _count_sections(self, sections: list[Section]) -> int:
        total = 0
        for section in sections:
            total += 1
            total += self._count_sections(section.sections)
        return total

    def _count_figures_in_division(self, division: Division) -> int:
        total = self._count_figures_in_blocks(division.blocks)
        for section in division.sections:
            total += self._count_figures_in_section(section)
        return total

    def _count_figures_in_section(self, section: Section) -> int:
        total = self._count_figures_in_blocks(section.blocks)
        for child in section.sections:
            total += self._count_figures_in_section(child)
        return total

    def _count_figures_in_blocks(self, blocks) -> int:
        total = 0
        for block in blocks:
            if isinstance(block, FigureBlock):
                total += 1
            elif isinstance(block, QuoteBlock):
                total += self._count_figures_in_blocks(block.blocks)
            elif isinstance(block, ListBlock):
                for item in block.items:
                    total += self._count_figures_in_blocks(item.blocks)
        return total

    def _write_report(self, result: PdfBuildResult) -> None:
        duration = result.finished_at - result.started_at

        lines = [
            "Build PDF Impressions — rapport",
            "=" * 32,
            "",
            f"Début : {result.started_at.isoformat(sep=' ', timespec='seconds')}",
            f"Fin   : {result.finished_at.isoformat(sep=' ', timespec='seconds')}",
            f"Durée : {duration}",
            "",
            f"XML source : {result.xml_path}",
            f"Dossier de sortie : {result.output_dir}",
            f"Fichier LaTeX : {result.tex_path}",
            f"Fichier PDF : {result.pdf_path}",
            f"Log LaTeX : {result.log_path}",
            "",
            f"Succès : {'oui' if result.success else 'non'}",
        ]

        if result.error_message:
            lines.extend(["", f"Erreur : {result.error_message}"])

        lines.extend(
            [
                "",
                "Statistiques",
                "-" * 12,
                f"Divisions : {result.stats.divisions}",
                f"Sections  : {result.stats.sections}",
                f"Figures   : {result.stats.figures}",
                f"Notes     : {result.stats.notes}",
            ]
        )

        lines.append("")
        lines.append("Commandes exécutées")
        lines.append("-" * 19)
        if result.commands:
            for command in result.commands:
                lines.append(" ".join(command))
        else:
            lines.append("Aucune compilation exécutée.")

        lines.append("")
        lines.append("Avertissements")
        lines.append("-" * 14)
        if result.warnings:
            for warning in result.warnings:
                lines.append(f"- {warning}")
        else:
            lines.append("Aucun avertissement.")

        result.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Fonction de confort
# ---------------------------------------------------------------------------


def build_pdf_from_normalized_tei(
    xml_path: str | Path,
    output_dir: str | Path,
    *,
    latex_engine: str = "lualatex",
    compile_pdf: bool = True,
) -> PdfBuildResult:
    """Fonction de confort pour lancer un build PDF en une ligne."""

    builder = PdfBuilder(
        latex_engine=latex_engine,
        compile_pdf=compile_pdf,
    )
    return builder.build_from_normalized_tei(xml_path, output_dir)
