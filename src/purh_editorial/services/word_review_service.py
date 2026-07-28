from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REVISION_XML_MARKERS = (
    b"<w:ins",
    b"<w:del",
    b"<w:moveFrom",
    b"<w:moveTo",
)


class WordReviewError(RuntimeError):
    """Erreur explicite lors de la production d'un DOCX de revision Word."""


@dataclass(slots=True)
class WordReviewResult:
    original_path: Path
    revised_path: Path
    output_path: Path
    has_tracked_changes: bool


def document_contains_tracked_changes(path: Path) -> bool:
    """Detecte des revisions Word dans les parties XML d'un fichier DOCX."""

    docx_path = Path(path)
    if docx_path.suffix.lower() != ".docx":
        raise WordReviewError(f"Extension non prise en charge pour la detection des revisions : {docx_path}")

    try:
        with zipfile.ZipFile(docx_path) as archive:
            for name in archive.namelist():
                if not name.startswith("word/") or not name.endswith(".xml"):
                    continue
                payload = archive.read(name)
                if any(marker in payload for marker in REVISION_XML_MARKERS):
                    return True
    except (OSError, zipfile.BadZipFile) as exc:
        raise WordReviewError(f"Fichier DOCX illisible pour la detection des revisions : {docx_path}") from exc

    return False


def _is_windows() -> bool:
    return sys.platform == "win32"


def _create_word_application() -> Any:
    if not _is_windows():
        raise WordReviewError("Microsoft Word n'est disponible pour ce service que sous Windows.")

    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise WordReviewError(
            "pywin32 est requis pour automatiser Microsoft Word sous Windows."
        ) from exc

    try:
        return DispatchEx("Word.Application")
    except Exception as exc:  # pragma: no cover - depend de l'installation Word.
        raise WordReviewError("Microsoft Word est indisponible ou ne peut pas etre automatise.") from exc


def _word_constants(word_app: Any) -> Any:
    """Charge les constantes de la bibliotheque de types de l'instance isolee."""

    try:
        from win32com.client import constants
        from win32com.client import gencache
    except ImportError as exc:
        raise WordReviewError(
            "pywin32 est requis pour acceder aux constantes Microsoft Word."
        ) from exc

    try:
        constants.wdCompareDestinationNew
    except AttributeError:
        try:
            type_info = word_app._oleobj_.GetTypeInfo()
            type_library, _ = type_info.GetContainingTypeLib()
            guid, lcid, _syskind, major, minor, _flags = type_library.GetLibAttr()
            gencache.EnsureModule(guid, lcid, major, minor)
            constants.wdCompareDestinationNew
        except Exception as exc:
            raise WordReviewError(
                "Impossible de charger les constantes de Microsoft Word pour la comparaison."
            ) from exc

    return constants


class WordReviewService:
    """Cree un troisieme DOCX de revision par comparaison native Microsoft Word."""

    review_author = "PURH Editorial"

    def create_review_document(
        self,
        *,
        original_path: Path,
        revised_path: Path,
        output_path: Path,
    ) -> WordReviewResult:
        original = self._validated_input_path(original_path, "document original")
        revised = self._validated_input_path(revised_path, "document candidat")
        output = Path(output_path).expanduser().resolve()
        self._validate_distinct_paths(original, revised, output)

        temp_path: Path | None = None
        word_app = None
        original_doc = None
        revised_doc = None
        comparison_doc = None

        try:
            word_app = _create_word_application()
            constants = _word_constants(word_app)
            self._prepare_isolated_application(word_app)

            original_doc = self._open_source_document(word_app, original)
            revised_doc = self._open_source_document(word_app, revised)
            comparison_doc = self._compare_documents(word_app, constants, original_doc, revised_doc)

            temp_path = self._make_neighbor_temp_path(output)
            self._save_review_document(comparison_doc, constants, temp_path)
            self._close_document(comparison_doc)
            comparison_doc = None

            if not temp_path.exists():
                raise WordReviewError(f"Fichier de sortie non produit par Word : {temp_path}")

            has_tracked_changes = document_contains_tracked_changes(temp_path)
            os.replace(temp_path, output)
            temp_path = None
            return WordReviewResult(
                original_path=original,
                revised_path=revised,
                output_path=output,
                has_tracked_changes=has_tracked_changes,
            )
        except WordReviewError:
            raise
        except Exception as exc:
            raise WordReviewError(f"Comparaison Word echouee : {exc}") from exc
        finally:
            self._close_document(comparison_doc)
            self._close_document(revised_doc)
            self._close_document(original_doc)
            # Relacher les proxies COM avant de quitter l'instance que ce service
            # a creee : leur finalisation apres Quit() peut provoquer un appel RPC
            # tardif vers Word.
            comparison_doc = None
            revised_doc = None
            original_doc = None
            self._quit_application(word_app)
            word_app = None
            self._remove_temp_file(temp_path)

    @staticmethod
    def _validated_input_path(path: Path, label: str) -> Path:
        candidate = Path(path).expanduser().resolve()
        if candidate.suffix.lower() != ".docx":
            raise WordReviewError(f"Extension non prise en charge pour {label} : {candidate}")
        if not candidate.exists():
            raise WordReviewError(f"Document source absent pour {label} : {candidate}")
        if not candidate.is_file():
            raise WordReviewError(f"Document source invalide pour {label} : {candidate}")
        return candidate

    @staticmethod
    def _validate_distinct_paths(original: Path, revised: Path, output: Path) -> None:
        if output.suffix.lower() != ".docx":
            raise WordReviewError(f"Extension non prise en charge pour la sortie : {output}")
        if original == revised:
            raise WordReviewError("Le document original et le document candidat doivent etre distincts.")
        if output == original or output == revised:
            raise WordReviewError("Le fichier de sortie ne doit pas ecraser un document source.")

    @staticmethod
    def _prepare_isolated_application(word_app: Any) -> None:
        try:
            word_app.Visible = False
        except Exception:
            pass
        try:
            word_app.DisplayAlerts = 0
        except Exception:
            pass

    @staticmethod
    def _open_source_document(word_app: Any, path: Path) -> Any:
        return word_app.Documents.Open(
            FileName=str(path),
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )

    def _compare_documents(self, word_app: Any, constants: Any, original_doc: Any, revised_doc: Any) -> Any:
        return word_app.CompareDocuments(
            OriginalDocument=original_doc,
            RevisedDocument=revised_doc,
            Destination=constants.wdCompareDestinationNew,
            Granularity=constants.wdGranularityCharLevel,
            CompareFormatting=False,
            CompareCaseChanges=True,
            CompareWhitespace=True,
            CompareTables=True,
            CompareHeaders=True,
            CompareFootnotes=True,
            CompareTextboxes=True,
            CompareFields=True,
            CompareComments=False,
            CompareMoves=False,
            RevisedAuthor=self.review_author,
        )

    @staticmethod
    def _make_neighbor_temp_path(output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(
            prefix=f".{output.stem}.",
            suffix=".tmp.docx",
            dir=output.parent,
        )
        os.close(handle)
        temp_path = Path(name)
        temp_path.unlink()
        return temp_path

    @staticmethod
    def _save_review_document(comparison_doc: Any, constants: Any, temp_path: Path) -> None:
        comparison_doc.SaveAs2(
            FileName=str(temp_path),
            FileFormat=constants.wdFormatXMLDocument,
            AddToRecentFiles=False,
        )

    @staticmethod
    def _close_document(document: Any) -> None:
        if document is None:
            return
        try:
            document.Close(SaveChanges=False)
        except Exception:
            pass

    @staticmethod
    def _quit_application(word_app: Any) -> None:
        if word_app is None:
            return
        try:
            word_app.Quit()
        except Exception:
            pass

    @staticmethod
    def _remove_temp_file(temp_path: Path | None) -> None:
        if temp_path is None:
            return
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass
