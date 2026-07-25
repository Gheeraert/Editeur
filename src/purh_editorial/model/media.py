from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ImageAsset:
    """Un média incorporé, dédupliqué par sha256 (voir docx_importer.py)."""

    asset_id: str
    filename: str
    content_type: str
    data: bytes
    sha256: str
    width_emu: int | None = None
    height_emu: int | None = None
    alt_text: str = ""
    title: str = ""
    source_part: str = ""


@dataclass(slots=True)
class ImageOccurrence:
    """Une apparition d'un ImageAsset dans le document, a un emplacement logique donne.

    `placement` : "inline" | "anchor" | "note" | "table" | "header_footer".
    `target_ref` : block_id ou note_id contenant l'occurrence.
    `order` : position globale dans le document (ordre logique de lecture).
    """

    occurrence_id: str
    asset_ref: str
    placement: str
    target_ref: str
    order: int
    width_emu: int | None = None
    height_emu: int | None = None
    alt_text: str = ""
    title: str = ""
    caption: str | None = None
    external_link: str | None = None
    anchor_normalized_to_inline: bool = False
    original_xml: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ComplexObjectOccurrence:
    """Un objet OOXML non pris en charge comme image ordinaire (graphique, SmartArt,
    OLE, equation, video, modele 3D) : jamais confondu avec une image, jamais
    supprime silencieusement. `fallback_asset_ref` pointe vers un ImageAsset si un
    apercu raster (fallback) a pu etre extrait (ex. OLE avec v:imagedata)."""

    occurrence_id: str
    object_type: str
    target_ref: str
    order: int
    placement: str = "inline"
    fallback_asset_ref: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
