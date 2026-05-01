from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from lxml import etree

from .utils import NSMAP, slugify, xml_id, set_xml_id


@dataclass(slots=True)
class NormalizeReport:
    """Journal de normalisation du TEI avant transformation XSLT."""

    assigned_ids: int = 0
    notes_numbered: int = 0
    figure_media_resolved: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_lines(self) -> list[str]:
        return [
            f"Identifiants attribués : {self.assigned_ids}",
            f"Notes numérotées : {self.notes_numbered}",
            f"Figures/médias explicitement résolus : {self.figure_media_resolved}",
            *[f"Avertissement : {warning}" for warning in self.warnings],
        ]


class TeiNormalizer:
    """Normalisation légère et pragmatique d'un TEI Métopes pour le rendu web."""

    def normalize(self, tree: etree._ElementTree) -> NormalizeReport:
        report = NormalizeReport()
        self._ensure_ids(tree, report)
        self._number_notes(tree, report)
        self._resolve_figure_media(tree, report)
        return report

    def _ensure_ids(self, tree: etree._ElementTree, report: NormalizeReport) -> None:
        counters: defaultdict[str, int] = defaultdict(int)
        seen_ids: set[str] = set()
        candidates = tree.xpath(
            "//*[@xml:id] | //tei:group | //tei:div | //tei:head | //tei:p | //tei:figure | //tei:note | //tei:listBibl | //tei:bibl",
            namespaces=NSMAP,
        )
        for element in candidates:
            current_id = xml_id(element)
            if current_id and current_id not in seen_ids:
                seen_ids.add(current_id)
                continue

            local = etree.QName(element).localname
            if local == "head":
                base = slugify(" ".join(element.itertext()), fallback="head")
            elif local == "group":
                base = slugify(element.get("type", "group"), fallback="group")
            elif local == "div":
                base = slugify(element.get("type", "div"), fallback="div")
            else:
                base = local

            while True:
                counters[base] += 1
                candidate_id = f"{base}-{counters[base]:03d}"
                if candidate_id not in seen_ids:
                    break

            set_xml_id(element, candidate_id)
            seen_ids.add(candidate_id)
            report.assigned_ids += 1

    def _number_notes(self, tree: etree._ElementTree, report: NormalizeReport) -> None:
        for index, note in enumerate(tree.xpath("//tei:note", namespaces=NSMAP), start=1):
            note.set("n", str(index))
            report.notes_numbered += 1

    def _resolve_figure_media(self, tree: etree._ElementTree, report: NormalizeReport) -> None:
        figures = tree.xpath("//tei:figure", namespaces=NSMAP)
        for figure in figures:
            if figure.xpath("./tei:graphic[@url] | ./tei:media[@url]", namespaces=NSMAP):
                report.figure_media_resolved += 1
                continue
            head_text = " ".join(figure.xpath("./tei:head//text()", namespaces=NSMAP)).strip()
            if head_text and not figure.xpath("./tei:graphic | ./tei:media", namespaces=NSMAP):
                report.warnings.append(f"Figure sans ressource explicite : {head_text[:100]}")
