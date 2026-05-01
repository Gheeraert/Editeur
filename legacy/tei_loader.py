from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

from lxml import etree

from .utils import NSMAP, short_text


@dataclass(slots=True)
class LoadReport:
    """Journal de chargement et de validation primaire du corpus TEI."""

    master_path: Path
    included_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [f"Fichier maître : {self.master_path}"]
        if self.included_files:
            lines.append("Fichiers inclus :")
            lines.extend(f"- {path}" for path in self.included_files)
        if self.info:
            lines.append("Informations :")
            lines.extend(f"- {line}" for line in self.info)
        if self.warnings:
            lines.append("Avertissements :")
            lines.extend(f"- {line}" for line in self.warnings)
        return "\n".join(lines) + "\n"


class TeiLoader:
    """Charge un fichier TEI, résout les XInclude et produit un arbre unifié."""

    def __init__(self) -> None:
        self.parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)

    def load_master(self, master_path: Path) -> tuple[etree._ElementTree, LoadReport]:
        master_path = master_path.resolve()
        report = LoadReport(master_path=master_path)
        tree = etree.parse(str(master_path), self.parser)
        include_hrefs = self._collect_include_hrefs(tree)
        report.included_files = [(master_path.parent / unquote(href)).resolve() for href in include_hrefs]

        missing = [path for path in report.included_files if not path.exists()]
        for path in missing:
            report.warnings.append(f"Fichier inclus introuvable : {path}")

        self._resolve_xincludes(tree.getroot(), master_path.parent, report)
        report.info.append(
            f"XInclude résolu ({len(include_hrefs)} inclusion(s) repérée(s) avant résolution)."
        )

        self._basic_checks(tree, report)
        return tree, report

    def load_single(self, xml_path: Path) -> tuple[etree._ElementTree, LoadReport]:
        xml_path = xml_path.resolve()
        report = LoadReport(master_path=xml_path)
        tree = etree.parse(str(xml_path), self.parser)
        self._basic_checks(tree, report)
        return tree, report

    def _resolve_xincludes(self, root: etree._Element, base_dir: Path, report: LoadReport) -> None:
        includes = root.xpath('.//xi:include', namespaces=NSMAP)
        for include in includes:
            href = include.get('href')
            if not href:
                continue
            target = (base_dir / unquote(href)).resolve()
            if not target.exists():
                continue

            included_tree = etree.parse(str(target), self.parser)
            self._resolve_xincludes(included_tree.getroot(), target.parent, report)
            metadata = self._extract_included_metadata(included_tree)
            inserted_nodes = self._select_included_nodes(included_tree)

            parent = include.getparent()
            if parent is None:
                continue
            for key, value in metadata.items():
                if value:
                    parent.set(key, value)
            parent.set("data-include-href", href)

            index = parent.index(include)
            parent.remove(include)
            for offset, node in enumerate(inserted_nodes):
                parent.insert(index + offset, node)

    def _extract_included_metadata(self, tree: etree._ElementTree) -> dict[str, str]:
        title = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main'])[1])",
            namespaces=NSMAP,
        )
        subtitle = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='sub'])[1])",
            namespaces=NSMAP,
        )
        authors = []
        for author in tree.xpath('/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author', namespaces=NSMAP):
            name = " ".join(author.xpath('.//tei:persName//text() | .//tei:name//text()', namespaces=NSMAP)).strip()
            if not name:
                name = " ".join(author.xpath('./text()')).strip() or " ".join(author.xpath('.//text()')).strip()
            affiliations = [
                " ".join(aff.xpath('.//text()')).strip()
                for aff in author.xpath('./tei:affiliation', namespaces=NSMAP)
                if " ".join(aff.xpath('.//text()')).strip()
            ]
            if name:
                authors.append("@@".join([name, *affiliations]))
        return {
            "data-page-title": title,
            "data-page-subtitle": subtitle,
            "data-page-authors": "||".join(authors),
        }

    def _select_included_nodes(self, tree: etree._ElementTree) -> list[etree._Element]:
        root = tree.getroot()
        text_nodes = root.xpath('/tei:TEI/tei:text', namespaces=NSMAP)
        if text_nodes:
            text_node = text_nodes[0]
            return [etree.fromstring(etree.tostring(child)) for child in text_node]
        return [etree.fromstring(etree.tostring(root))]

    def _collect_include_hrefs(self, tree: etree._ElementTree) -> list[str]:
        hrefs: list[str] = []
        for node in tree.xpath("//xi:include", namespaces=NSMAP):
            href = node.get("href")
            if href:
                hrefs.append(href)
        return hrefs

    def _basic_checks(self, tree: etree._ElementTree, report: LoadReport) -> None:
        title = tree.xpath("string(/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main'][1])", namespaces=NSMAP)
        if title.strip():
            report.info.append(f"Titre principal : {short_text(title.strip())}")
        else:
            report.warnings.append("Titre principal absent ou vide dans le teiHeader.")

        notes = len(tree.xpath("//tei:note", namespaces=NSMAP))
        figures = len(tree.xpath("//tei:figure", namespaces=NSMAP))
        graphics = len(tree.xpath("//tei:graphic", namespaces=NSMAP))
        media = len(tree.xpath("//tei:media", namespaces=NSMAP))
        report.info.append(
            f"Éléments repérés : {notes} note(s), {figures} figure(s), {graphics} graphic(s), {media} media(s)."
        )


def load_many(xml_files: Iterable[Path]) -> list[tuple[etree._ElementTree, LoadReport]]:
    loader = TeiLoader()
    result: list[tuple[etree._ElementTree, LoadReport]] = []
    for xml_path in xml_files:
        result.append(loader.load_single(Path(xml_path)))
    return result
