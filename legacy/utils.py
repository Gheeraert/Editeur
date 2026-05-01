from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path


XML_NS = "http://www.w3.org/XML/1998/namespace"
TEI_NS = "http://www.tei-c.org/ns/1.0"
XI_NS = "http://www.w3.org/2001/XInclude"
NSMAP = {"tei": TEI_NS, "xi": XI_NS, "xml": XML_NS}


_slug_pattern = re.compile(r"[^a-z0-9]+")


def slugify(value: str, fallback: str = "section") -> str:
    """Produit un slug simple, stable et lisible."""
    normalized = value.strip().lower()
    normalized = normalized.replace("œ", "oe").replace("æ", "ae")
    normalized = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("’", "-").replace("'", "-")
    normalized = _slug_pattern.sub("-", normalized)
    normalized = normalized.strip("-")
    return normalized or fallback


def xml_id(element) -> str | None:
    """Retourne l'identifiant XML d'un élément TEI, s'il existe."""
    return element.get(f"{{{XML_NS}}}id")


def set_xml_id(element, value: str) -> None:
    """Affecte un identifiant XML à un élément."""
    element.set(f"{{{XML_NS}}}id", value)


def short_text(value: str | None, max_len: int = 80) -> str:
    """Tronque un texte pour l'affichage dans les journaux de build."""
    if not value:
        return ""
    value = " ".join(value.split())
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def ensure_dir(path: Path) -> None:
    """Crée un dossier et ses parents si nécessaire."""
    path.mkdir(parents=True, exist_ok=True)


def html_escape_attr(value: str) -> str:
    """Échappe un attribut HTML pour un usage sûr dans des chaînes."""
    return html.escape(value, quote=True)
