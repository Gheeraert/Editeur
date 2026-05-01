from __future__ import annotations

import copy
import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from lxml import etree

from .config import BuildConfig
from .normalizer import NormalizeReport, TeiNormalizer
from .site_structure import AuthorEntry, NavItem, PageDef, SiteMeta, SiteStructureBuilder
from .tei_loader import LoadReport, TeiLoader, load_many
from .utils import NSMAP, ensure_dir


@dataclass(slots=True)
class BuildResult:
    output_dir: Path
    html_path: Path
    normalized_tei_path: Path | None
    report_path: Path

@dataclass(slots=True)
class ThemeAssets:
    cover_href: str | None = None
    university_logo_href: str | None = None
    purh_logo_href: str | None = None
    pdf_href: str | None = None
    footer_logo_href: str | None = None

class SiteBuilder:
    """Orchestre le chargement, la normalisation et le rendu multi-pages."""

    def __init__(self) -> None:
        self.loader = TeiLoader()
        self.normalizer = TeiNormalizer()
        self.structure_builder = SiteStructureBuilder()
        self.resources_dir = Path(__file__).parent / "resources"
        self.fragment_xslt = etree.XSLT(etree.parse(str(self.resources_dir / "tei_to_html.xsl")))

    def build_from_master(self, master_xml: Path, config: BuildConfig) -> BuildResult:
        tree, load_report = self.loader.load_master(master_xml)
        normalize_report = self.normalizer.normalize(tree)
        return self._finalize_build(tree, config, load_report, normalize_report)

    def build_from_many(self, xml_files: list[Path], output_root: Path, assets_dir: Path | None = None) -> list[BuildResult]:
        results: list[BuildResult] = []
        for tree, load_report in load_many(xml_files):
            normalize_report = self.normalizer.normalize(tree)
            target_dir = output_root / Path(load_report.master_path).stem
            config = BuildConfig(output_dir=target_dir, assets_dir=assets_dir)
            results.append(self._finalize_build(tree, config, load_report, normalize_report))
        return results

    def _finalize_build(
        self,
        tree: etree._ElementTree,
        config: BuildConfig,
        load_report: LoadReport,
        normalize_report: NormalizeReport,
    ) -> BuildResult:
        ensure_dir(config.output_dir)
        ensure_dir(config.output_assets_dir)
        self._copy_static_resources(config.output_assets_dir)
        self._copy_user_assets(config.assets_dir, config.output_assets_dir)

        normalized_tei_path: Path | None = config.output_dir / "book.normalized.xml"
        tree.write(
            str(normalized_tei_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

        site_meta, pages, nav = self.structure_builder.build(tree)
        theme_assets = self._discover_theme_assets(config.output_assets_dir)
        back_cover_html, back_cover_source = self._resolve_back_cover_html(tree, config.output_assets_dir)
        self._write_index_page(
            config.output_dir,
            site_meta,
            nav,
            theme_assets,
            normalized_tei_href=normalized_tei_path.name,
            back_cover_html=back_cover_html,
        )
        for page in pages:
            self._write_content_page(config.output_dir, tree, site_meta, nav, page, theme_assets)

        report_path = config.output_dir / "build_report.txt"
        report_lines = [
            load_report.as_text(),
            "Normalisation :",
            *normalize_report.as_lines(),
            "",
            f"Pages générées : {1 + len(pages)}",
        ]
        report_lines.extend(f"- {page.file_name} ← {page.title}" for page in pages)
        if theme_assets.cover_href:
            report_lines.append(f"Couverture détectée : {theme_assets.cover_href}")
        if theme_assets.university_logo_href:
            report_lines.append(f"Logo université : {theme_assets.university_logo_href}")
        if theme_assets.purh_logo_href:
            report_lines.append(f"Logo PURH : {theme_assets.purh_logo_href}")
        if theme_assets.pdf_href:
            report_lines.append(f"PDF détecté : {theme_assets.pdf_href}")
        if back_cover_source:
            report_lines.append(f"Quatrième de couverture : {back_cover_source}")
        report_path.write_text("\n".join(report_lines), encoding="utf-8")

        return BuildResult(
            output_dir=config.output_dir,
            html_path=config.output_dir / "index.html",
            normalized_tei_path=normalized_tei_path,
            report_path=report_path,
        )

    def _copy_static_resources(self, output_assets_dir: Path) -> None:
        for name in ("site.css", "app.js"):
            shutil.copy2(self.resources_dir / name, output_assets_dir / name)

    def _copy_user_assets(self, user_assets_dir: Path | None, output_assets_dir: Path) -> None:
        if not user_assets_dir or not user_assets_dir.exists():
            return
        for child in user_assets_dir.iterdir():
            dst = output_assets_dir / child.name
            if child.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(child, dst)
            else:
                shutil.copy2(child, dst)

    def _write_index_page(
            self,
            output_dir: Path,
            site_meta: SiteMeta,
            nav: list[NavItem],
            theme_assets: ThemeAssets,
            normalized_tei_href: str,
            back_cover_html: str | None,
    ) -> None:
        nav_html = self._render_sidebar(nav, current_file_name=None)
        creators_value = html.escape(" · ".join(site_meta.creators)) if site_meta.creators else ""
        hero_parts = ['<section class="home-hero">', '<div class="home-hero-grid">']
        hero_parts.append('<div class="home-hero-text">')
        hero_parts.append('<p class="eyebrow">Livre web PURH</p>')
        hero_parts.append(f'<h1>{html.escape(site_meta.title)}</h1>')
        if site_meta.subtitle:
            hero_parts.append(f'<p class="subtitle">{html.escape(site_meta.subtitle)}</p>')
        if creators_value:
            hero_parts.append(f'<p class="meta-line">{creators_value}</p>')
        if site_meta.publisher or site_meta.publication_year:
            meta_bits = [bit for bit in (site_meta.publisher, site_meta.publication_year) if bit]
            hero_parts.append(f'<p class="meta-line">{" · ".join(html.escape(bit) for bit in meta_bits)}</p>')
        if back_cover_html:
            hero_parts.append(f'<div class="hero-back-cover">{back_cover_html}</div>')
        hero_parts.append('</div>')
        hero_parts.append(self._render_cover_link(theme_assets, compact=False))
        hero_parts.append('</div></section>')
        hero_parts.append(self._render_home_downloads(normalized_tei_href, theme_assets.pdf_href))
        hero_parts.append('<section class="home-panel"><h2>Sommaire</h2>')
        hero_parts.append(self._render_toc(nav))
        hero_parts.append('</section>')
        hero_parts.append(self._render_footer(theme_assets))
        page_html = self._wrap_html(
            page_title=site_meta.title,
            site_meta=site_meta,
            nav_html=nav_html,
            content_html=''.join(hero_parts),
            theme_assets=theme_assets,
            page_grid_class='page-grid page-grid--home',
            abstract_html=back_cover_html,
        )
        (output_dir / 'index.html').write_text(page_html, encoding='utf-8')

    def _write_content_page(
        self,
        output_dir: Path,
        tree: etree._ElementTree,
        site_meta: SiteMeta,
        nav: list[NavItem],
        page: PageDef,
        theme_assets: ThemeAssets,
    ) -> None:
        page_group = self._find_page_group(tree, page.node_id)
        if page_group is None:
            return
        fragment_html = self._render_page_fragment(page_group)
        nav_html = self._render_sidebar(nav, current_file_name=page.file_name)
        page_header = self._render_page_header(page, theme_assets)
        credits = self._render_credit_block(page, site_meta)
        pager = self._render_prev_next(page, nav)
        full_content = page_header + fragment_html + credits + pager + self._render_footer(theme_assets)
        page_html = self._wrap_html(
            page_title=f"{page.title} — {site_meta.title}",
            site_meta=site_meta,
            nav_html=nav_html,
            content_html=full_content,
            theme_assets=theme_assets,
            page_grid_class='page-grid',
            page=page,
        )
        (output_dir / page.file_name).write_text(page_html, encoding='utf-8')

    def _find_page_group(self, tree: etree._ElementTree, node_id: str) -> etree._Element | None:
        matches = tree.xpath(f"//*[@xml:id='{node_id}']", namespaces=NSMAP)
        return matches[0] if matches else None

    def _render_page_fragment(self, page_group: etree._Element) -> str:
        cloned = copy.deepcopy(page_group)
        self._strip_redundant_title_pages(cloned)
        self._renumber_fragment_notes(cloned)
        fragment_tree = etree.ElementTree(cloned)
        result = self.fragment_xslt(
            fragment_tree,
            assets_image_base=etree.XSLT.strparam('assets/images'),
            assets_audio_base=etree.XSLT.strparam('assets/audio'),
            assets_video_base=etree.XSLT.strparam('assets/video'),
        )
        return str(result)

    def _strip_redundant_title_pages(self, root: etree._Element) -> None:
        for title_page in root.xpath(".//tei:front/tei:div[@type='titlePage']", namespaces=NSMAP):
            parent = title_page.getparent()
            if parent is not None:
                parent.remove(title_page)

    def _renumber_fragment_notes(self, root: etree._Element) -> None:
        for index, note in enumerate(root.xpath('.//tei:note', namespaces=NSMAP), start=1):
            note.set('n', str(index))

    def _render_sidebar(self, nav: list[NavItem], current_file_name: str | None) -> str:
        nav_items = self.structure_builder.build_nav_for_page(nav, current_file_name)
        return (
            '<nav class="sidebar-nav" aria-label="Sommaire du livre">'
            '<div class="sidebar-top-links">'
            '<a class="sidebar-back-link" href="https://purh.univ-rouen.fr/" target="_blank" rel="noopener">'
            'Retour au catalogue des PURH'
            '</a>'
            '<a class="sidebar-home" href="index.html">Présentation du volume</a>'
            '</div>'
            f'{self._render_nav_list(nav_items)}'
            '</nav>'
        )

    def _render_nav_list(self, items: list[NavItem]) -> str:
        if not items:
            return ''
        html_parts = ['<ul class="nav-list">']
        for item in items:
            classes = ['nav-item']
            if item.children:
                classes.append('has-children')
            if item.is_current:
                classes.append('is-current')
            html_parts.append(f'<li class="{" ".join(classes)}">')
            if item.href:
                html_parts.append(f'<a href="{html.escape(item.href)}">{html.escape(item.title)}</a>')
            else:
                html_parts.append(f'<span class="nav-label">{html.escape(item.title)}</span>')
            html_parts.append(self._render_nav_list(item.children))
            html_parts.append('</li>')
        html_parts.append('</ul>')
        return ''.join(html_parts)

    def _render_toc(self, nav: list[NavItem]) -> str:
        return self._render_nav_list(nav)

    def _render_home_downloads(self, normalized_tei_href: str, pdf_href: str | None) -> str:
        parts = ['<section class="home-panel home-panel--downloads">']
        parts.append('<h2>Téléchargements</h2>')
        parts.append('<div class="download-buttons">')
        parts.append(
            f'<a class="download-button" href="{html.escape(normalized_tei_href)}" download>'
            'Télécharger le XML - TEI'
            '</a>'
        )
        if pdf_href:
            parts.append(
                f'<a class="download-button" href="{html.escape(pdf_href)}" download>'
                'Télécharger le PDF'
                '</a>'
            )
        parts.append('</div></section>')
        return ''.join(parts)

    def _resolve_back_cover_html(self, tree: etree._ElementTree, output_assets_dir: Path) -> tuple[str | None, str | None]:
        xml_html = self._extract_back_cover_from_xml(tree)
        if xml_html:
            return xml_html, 'XML (abstract rend="4e-couv")'
        assets_html = self._read_back_cover_from_assets(output_assets_dir)
        if assets_html:
            return assets_html, 'assets/quatrieme'
        return None, None

    def _extract_back_cover_from_xml(self, tree: etree._ElementTree) -> str | None:
        nodes = tree.xpath(
            "/tei:TEI/tei:teiHeader/tei:profileDesc/tei:abstract[@rend='4e-couv']",
            namespaces=NSMAP,
        )
        if not nodes:
            return None

        abstract_node = nodes[0]
        if not ''.join(abstract_node.itertext()).strip():
            return None

        wrapper = etree.Element(f"{{{NSMAP['tei']}}}div", nsmap={'tei': NSMAP['tei']})
        for child in abstract_node:
            wrapper.append(copy.deepcopy(child))

        fragment_tree = etree.ElementTree(wrapper)
        result = self.fragment_xslt(
            fragment_tree,
            assets_image_base=etree.XSLT.strparam('assets/images'),
            assets_audio_base=etree.XSLT.strparam('assets/audio'),
            assets_video_base=etree.XSLT.strparam('assets/video'),
        )
        return str(result)

    def _read_back_cover_from_assets(self, output_assets_dir: Path) -> str | None:
        back_cover_dir = output_assets_dir / 'quatrieme'
        if not back_cover_dir.exists() or not back_cover_dir.is_dir():
            return None

        markdown_files = sorted(
            path for path in back_cover_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {'.md', '.markdown'}
        )
        if markdown_files:
            content = markdown_files[0].read_text(encoding='utf-8').strip()
            return self._render_simple_markdown(content) if content else None

        html_files = sorted(
            path for path in back_cover_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {'.html', '.htm'}
        )
        if html_files:
            content = html_files[0].read_text(encoding='utf-8').strip()
            return content or None

        txt_files = sorted(
            path for path in back_cover_dir.iterdir()
            if path.is_file() and path.suffix.lower() == '.txt'
        )
        if txt_files:
            content = txt_files[0].read_text(encoding='utf-8').strip()
            return self._render_simple_markdown(content) if content else None

        return None

    def _render_simple_markdown(self, source: str) -> str:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", source.strip()) if block.strip()]
        if not blocks:
            return ''

        parts: list[str] = []
        list_buffer: list[str] = []

        def flush_list() -> None:
            nonlocal list_buffer
            if list_buffer:
                items = ''.join(f'<li>{self._render_markdown_inline(item)}</li>' for item in list_buffer)
                parts.append(f'<ul>{items}</ul>')
                list_buffer = []

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if lines and all(line.startswith(('- ', '* ')) for line in lines):
                list_buffer.extend(line[2:].strip() for line in lines)
                continue

            flush_list()
            merged = ' '.join(lines)
            parts.append(f'<p>{self._render_markdown_inline(merged)}</p>')

        flush_list()
        return ''.join(parts)

    def _render_markdown_inline(self, text: str) -> str:
        rendered = html.escape(text)
        substitutions = (
            (r'(?<!\*)\*\*(.+?)\*\*(?!\*)', r'<strong>\1</strong>'),
            (r'(?<!_)__(.+?)__(?!_)', r'<strong>\1</strong>'),
            (r'(?<!\*)\*(.+?)\*(?!\*)', r'<em>\1</em>'),
            (r'(?<!_)_(.+?)_(?!_)', r'<em>\1</em>'),
        )
        for pattern, replacement in substitutions:
            rendered = re.sub(pattern, replacement, rendered)
        return rendered

    def _render_page_header(self, page: PageDef, theme_assets: ThemeAssets) -> str:
        parts = ['<header class="page-header">', '<div class="page-header-grid">']
        parts.append(self._render_cover_link(theme_assets, compact=True))
        parts.append('<div class="page-header-main">')
        if page.section_chain:
            parts.append(f'<p class="eyebrow">{html.escape(" / ".join(page.section_chain))}</p>')
        parts.append(f'<h1>{html.escape(page.title)}</h1>')
        if page.subtitle:
            parts.append(f'<p class="subtitle">{html.escape(page.subtitle)}</p>')
        if page.author_entries:
            parts.append(self._render_author_block(page.author_entries))
        elif page.authors:
            parts.append(f'<p class="page-authors">{html.escape(" · ".join(page.authors))}</p>')
        parts.append('</div></div></header>')
        return ''.join(parts)

    def _render_author_block(self, author_entries: list[AuthorEntry]) -> str:
        parts = ['<div class="page-authors">']
        for entry in author_entries:
            parts.append('<div class="author-card">')
            parts.append(f'<div class="author-name">{html.escape(entry.name)}</div>')
            for affiliation in entry.affiliations:
                parts.append(f'<div class="author-affiliation">{html.escape(affiliation)}</div>')
            parts.append('</div>')
        parts.append('</div>')
        return ''.join(parts)

    def _render_credit_block(self, page: PageDef, site_meta: SiteMeta) -> str:
        page_creators = page.authors or site_meta.creators
        volume_title = site_meta.title
        if site_meta.subtitle:
            volume_title = f"{volume_title}. {site_meta.subtitle}"

        volume_creators_text = " ; ".join(site_meta.creators)
        role_label = site_meta.creator_role_label
        public_url = self._build_public_page_url(page.file_name, site_meta)
        doi_value = site_meta.doi.strip()
        doi_url = self._normalize_doi_url(doi_value) if doi_value else ""
        cite_heading = {
            "article": "Pour citer cette contribution",
            "chapter": "Pour citer ce chapitre",
        }.get(page.page_kind, "Pour citer cette page")

        suggestion = [html.escape(" ; ".join(page_creators))] if page_creators else []
        title_bit = page.title
        if page.subtitle:
            title_bit += f". {page.subtitle}"
        suggestion.append(f'« {html.escape(title_bit)} »')
        host = f'dans <em>{html.escape(volume_title)}</em>'
        if volume_creators_text and set(page_creators) != set(site_meta.creators):
            host += f', {html.escape(role_label)} : {html.escape(volume_creators_text)}'
        suggestion.append(host)
        if site_meta.publisher:
            suggestion.append(html.escape(site_meta.publisher))
        if site_meta.publication_year:
            suggestion.append(html.escape(site_meta.publication_year))
        if public_url:
            suggestion.append(f'URL : <a href="{html.escape(public_url)}">{html.escape(public_url)}</a>')
        if doi_url:
            suggestion.append(f'DOI : <a href="{html.escape(doi_url)}">{html.escape(doi_value)}</a>')
        suggestion.append('consulté le <time class="consultation-date"></time>')

        lines = ['<section class="credit-box">']
        lines.append('<h2>Crédits et citabilité</h2>')
        lines.append(f'<p class="credit-kicker">{cite_heading}</p>')
        lines.append('<dl class="credit-list">')
        if page_creators:
            lines.append(f'<p class="credit-names">{html.escape(" ; ".join(page_creators))}</p>')
        lines.append(f'<div><dt>{"Contribution" if page.page_kind == "article" else "Chapitre"}</dt><dd>{html.escape(page.title)}</dd></div>')
        if page.subtitle:
            lines.append(f'<div><dt>Sous-titre</dt><dd>{html.escape(page.subtitle)}</dd></div>')
        lines.append(f'<div><dt>Volume</dt><dd><em>{html.escape(site_meta.title)}</em></dd></div>')
        if site_meta.subtitle:
            lines.append(f'<div><dt>Sous-titre du volume</dt><dd>{html.escape(site_meta.subtitle)}</dd></div>')
        if site_meta.publisher:
            lines.append(f'<div><dt>Éditeur</dt><dd>{html.escape(site_meta.publisher)}</dd></div>')
        if site_meta.publication_year:
            lines.append(f'<div><dt>Année</dt><dd>{html.escape(site_meta.publication_year)}</dd></div>')
        if public_url:
            lines.append(f'<div><dt>URL</dt><dd><a href="{html.escape(public_url)}">{html.escape(public_url)}</a></dd></div>')
        if doi_url:
            lines.append(f'<div><dt>DOI</dt><dd><a href="{html.escape(doi_url)}">{html.escape(doi_value)}</a></dd></div>')
        lines.append('<div><dt>Date de consultation</dt><dd><time class="consultation-date"></time></dd></div>')
        lines.append('</dl>')
        lines.append(f'<p class="credit-citation"><strong>Référence suggérée</strong> : {". ".join(suggestion)}.</p>')
        lines.append('</section>')
        return ''.join(lines)

    def _build_public_page_url(self, file_name: str, site_meta: SiteMeta) -> str:
        base = site_meta.site_url.strip()
        if not base:
            return file_name
        if base.endswith('.html'):
            return urljoin(base, file_name)
        return urljoin(base.rstrip('/') + '/', file_name)

    def _normalize_doi_url(self, doi: str) -> str:
        if not doi:
            return ''
        if doi.startswith('http://') or doi.startswith('https://'):
            return doi
        return f'https://doi.org/{doi}'

    def _render_prev_next(self, page: PageDef, nav: list[NavItem]) -> str:
        flat: list[tuple[str, str]] = []
        self._flatten_nav(nav, flat)
        current_index = next((idx for idx, (href, _) in enumerate(flat) if href == page.file_name), None)
        if current_index is None:
            return ''
        previous_item = flat[current_index - 1] if current_index > 0 else None
        next_item = flat[current_index + 1] if current_index + 1 < len(flat) else None
        parts = ['<nav class="pager" aria-label="Navigation entre pages">']
        if previous_item:
            parts.append(f'<a class="pager-link" href="{html.escape(previous_item[0])}">← {html.escape(previous_item[1])}</a>')
        else:
            parts.append('<span></span>')
        if next_item:
            parts.append(f'<a class="pager-link pager-link--next" href="{html.escape(next_item[0])}">{html.escape(next_item[1])} →</a>')
        parts.append('</nav>')
        return ''.join(parts)

    def _flatten_nav(self, items: list[NavItem], flat: list[tuple[str, str]]) -> None:
        for item in items:
            if item.href:
                flat.append((item.href, item.title))
            if item.children:
                self._flatten_nav(item.children, flat)

    def _render_banner(self, site_meta: SiteMeta, theme_assets: ThemeAssets) -> str:
        press_label = 'Presses universitaires de Rouen et du Havre'
        book_label = html.escape(site_meta.title)
        subtitle_label = html.escape(site_meta.subtitle)
        creator_names = ' · '.join(html.escape(name) for name in site_meta.creators if name)

        parts = ['<header class="site-banner">', '<div class="site-banner-inner">']
        parts.append('<a class="site-banner-home" href="index.html" aria-label="Retour au sommaire">')
        if theme_assets.purh_logo_href:
            parts.append(f'<img class="site-logo site-logo--purh" src="{html.escape(theme_assets.purh_logo_href)}" alt="{press_label}">')
        else:
            parts.append('<span class="site-logo-text site-logo-text--dark">PURH</span>')
        parts.append('<div class="site-banner-titles">')
        parts.append(f'<div class="site-banner-label">{press_label}</div>')
        parts.append(f'<div class="site-banner-book">{book_label}</div>')
        if subtitle_label:
            parts.append(f'<div class="site-banner-subtitle">{subtitle_label}</div>')
        if creator_names:
            parts.append('<div class="site-banner-creators">')
            parts.append(f'<span class="site-banner-creators-names">{creator_names}</span>')
            parts.append('</div>')
        parts.append('</div>')
        parts.append('</a>')
        parts.append('<div class="site-banner-spacer"></div>')
        if theme_assets.university_logo_href:
            parts.append(f'<img class="site-logo site-logo--univ" src="{html.escape(theme_assets.university_logo_href)}" alt="Université de Rouen Normandie">')
        else:
            parts.append('<span class="site-logo-text site-logo-text--dark site-logo-text--univ">Université de Rouen Normandie</span>')
        parts.append('</div></header>')
        return ''.join(parts)

    def _render_cover_link(self, theme_assets: ThemeAssets, compact: bool) -> str:
        classes = 'book-cover-link book-cover-link--compact' if compact else 'book-cover-link'
        if theme_assets.cover_href:
            cover_href = html.escape(theme_assets.cover_href)
            return (
                f'<button type="button" class="{classes} book-cover-trigger" '
                f'data-lightbox-src="{cover_href}" '
                'data-lightbox-alt="Couverture de l’ouvrage" '
                'data-lightbox-caption="Couverture de l’ouvrage" '
                'aria-label="Agrandir la couverture">'
                f'<img class="book-cover-image" src="{cover_href}" alt="Couverture de l’ouvrage">'
                '</button>'
            )
        return (
            f'<div class="{classes} book-cover-link--placeholder" aria-hidden="true">'
            '<span class="book-cover-placeholder">Couverture</span>'
            '</div>'
        )

    def _discover_theme_assets(self, output_assets_dir: Path) -> ThemeAssets:
        image_exts = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif'}
        candidates = [
            path.relative_to(output_assets_dir).as_posix()
            for path in output_assets_dir.rglob('*')
            if path.is_file() and path.suffix.lower() in image_exts
        ]
        return ThemeAssets(
            cover_href=self._pick_asset(candidates, [
                ['images', 'cover'],
                ['images', 'couverture'],
                ['cover'],
                ['couverture'],
                ['premiere', 'couv'],
                ['1ere', 'couv'],
                ['couv'],
            ]),
            university_logo_href=self._pick_asset(candidates, [
                ['logos', 'universite'],
                ['logos', 'university'],
                ['logos', 'urn'],
                ['universite'],
                ['university'],
                ['urn'],
            ]),
            purh_logo_href=self._pick_asset(candidates, [
                ['logos', 'purh'],
                ['logos', 'presses'],
                ['purh'],
                ['presses'],
            ]),
            footer_logo_href=self._pick_asset(candidates, [
                ['logos', 'logo_footer'],
                ['logos', 'footer'],
            ]),
            pdf_href=self._discover_pdf_href(output_assets_dir),
        )

    def _pick_asset(self, candidates: list[str], token_sets: list[list[str]]) -> str | None:
        lowered = [(candidate, candidate.lower()) for candidate in candidates]
        for tokens in token_sets:
            for candidate, lower in lowered:
                if all(token in lower for token in tokens):
                    return f'assets/{candidate}'
        return None

    def _discover_pdf_href(self, output_assets_dir: Path) -> str | None:
        for child in output_assets_dir.iterdir():
            if child.is_dir() and child.name.lower() == "pdf":
                pdf_files = sorted(path for path in child.rglob("*.pdf") if path.is_file())
                if pdf_files:
                    relative = pdf_files[0].relative_to(output_assets_dir).as_posix()
                    return f'assets/{relative}'
        return None


    def _render_footer(self, theme_assets: ThemeAssets) -> str:
        parts = [
            '<footer class="site-footer">',
            '<p>',
            'Livre web créé avec le système ',
            '<a href="https://github.com/Gheeraert/impression" target="_blank" rel="noopener">Impressions</a>. ',
            'Impressions est une création des PURH et de la ',
            '<a href="https://ceen.hypotheses.org/" target="_blank" rel="noopener">chaire d’excellence en édition numérique</a>.',
            '</p>',
        ]
        if theme_assets.footer_logo_href:
            parts.append(
                '<div class="site-footer-logo-wrap">'
                '<a href="https://ceen.hypotheses.org/" target="_blank" rel="noopener">'
                f'<img class="site-footer-logo" src="{html.escape(theme_assets.footer_logo_href)}" '
                'alt="Logo de la chaire d’excellence en édition numérique">'
                '</a>'
                '</div>'
            )
        parts.append('</footer>')
        return ''.join(parts)


    def _full_volume_title(self, site_meta: SiteMeta) -> str:
        if site_meta.subtitle:
            return f"{site_meta.title}. {site_meta.subtitle}"
        return site_meta.title

    def _build_public_asset_url(self, asset_href: str, site_meta: SiteMeta) -> str:
        base = site_meta.site_url.strip()
        if not base:
            return asset_href
        if base.endswith('.html'):
            return urljoin(base, asset_href)
        return urljoin(base.rstrip('/') + '/', asset_href)

    def _strip_html(self, value: str) -> str:
        text_value = re.sub(r'<[^>]+>', ' ', value or '')
        return re.sub(r'\s+', ' ', text_value).strip()

    def _meta_tag(self, name: str, content: str) -> str:
        content = (content or '').strip()
        if not content:
            return ''
        return f'<meta name="{html.escape(name, quote=True)}" content="{html.escape(content, quote=True)}">'

    def _render_zotero_meta(
        self,
        site_meta: SiteMeta,
        theme_assets: ThemeAssets,
        page: PageDef | None = None,
        abstract_html: str | None = None,
    ) -> str:
        tags: list[str] = []
        volume_title = self._full_volume_title(site_meta)

        page_url = self._build_public_page_url(page.file_name if page is not None else 'index.html', site_meta)
        if page is None:
            citation_title = volume_title
            creator_tag = 'citation_editor' if site_meta.creator_role_label.lower().startswith('dir') else 'citation_author'
            for creator in site_meta.creators:
                tags.append(self._meta_tag(creator_tag, creator))
            tags.extend([
                self._meta_tag('citation_title', citation_title),
                self._meta_tag('citation_publisher', site_meta.publisher),
                self._meta_tag('citation_publication_date', site_meta.publication_year),
                self._meta_tag('citation_isbn', site_meta.isbn),
                self._meta_tag('citation_issn', site_meta.issn),
                self._meta_tag('citation_series_title', site_meta.collection_title),
                self._meta_tag('citation_series_number', site_meta.collection_number),
                self._meta_tag('citation_doi', site_meta.doi),
                self._meta_tag('citation_language', 'fr'),
                self._meta_tag('citation_pdf_url', self._build_public_asset_url(theme_assets.pdf_href, site_meta) if theme_assets.pdf_href else ''),
                self._meta_tag('citation_abstract_html_url', page_url),
                self._meta_tag('DC.Title', citation_title),
                self._meta_tag('DC.Type', 'book'),
                self._meta_tag('DC.Publisher', site_meta.publisher),
                self._meta_tag('DC.Date', site_meta.publication_year),
                self._meta_tag('DC.Identifier', page_url),
            ])
            if abstract_html:
                abstract_text = self._strip_html(abstract_html)
                tags.append(self._meta_tag('description', abstract_text))
                tags.append(self._meta_tag('DC.Description', abstract_text))
            for creator in site_meta.creators:
                dc_name = 'DC.Contributor' if creator_tag == 'citation_editor' else 'DC.Creator'
                tags.append(self._meta_tag(dc_name, creator))
        else:
            citation_title = page.title if not page.subtitle else f"{page.title}. {page.subtitle}"
            chapter_authors = page.authors or site_meta.creators
            for author in chapter_authors:
                tags.append(self._meta_tag('citation_author', author))
                tags.append(self._meta_tag('DC.Creator', author))
            if site_meta.creators and set(chapter_authors) != set(site_meta.creators):
                for editor in site_meta.creators:
                    tags.append(self._meta_tag('citation_editor', editor))
                    tags.append(self._meta_tag('DC.Contributor', editor))
            tags.extend([
                self._meta_tag('citation_title', citation_title),
                self._meta_tag('citation_book_title', volume_title),
                self._meta_tag('citation_publisher', site_meta.publisher),
                self._meta_tag('citation_publication_date', site_meta.publication_year),
                self._meta_tag('citation_isbn', site_meta.isbn),
                self._meta_tag('citation_issn', site_meta.issn),
                self._meta_tag('citation_series_title', site_meta.collection_title),
                self._meta_tag('citation_series_number', site_meta.collection_number),
                self._meta_tag('citation_language', 'fr'),
                self._meta_tag('citation_abstract_html_url', page_url),
                self._meta_tag('DC.Title', citation_title),
                self._meta_tag('DC.Type', 'bookSection'),
                self._meta_tag('DC.Relation', volume_title),
                self._meta_tag('DC.Publisher', site_meta.publisher),
                self._meta_tag('DC.Date', site_meta.publication_year),
                self._meta_tag('DC.Identifier', page_url),
            ])

        return '\n  '.join(tag for tag in tags if tag)

    def _wrap_html(
        self,
        page_title: str,
        site_meta: SiteMeta,
        nav_html: str,
        content_html: str,
        theme_assets: ThemeAssets,
        page_grid_class: str = 'page-grid',
        page: PageDef | None = None,
        abstract_html: str | None = None,
    ) -> str:
        banner = self._render_banner(site_meta, theme_assets)
        zotero_meta = self._render_zotero_meta(site_meta, theme_assets, page=page, abstract_html=abstract_html)
        return f'''<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(page_title)}</title>
  <link rel="stylesheet" href="assets/site.css">
  {zotero_meta}
</head>
<body>
  {banner}
  <div class="layout">
    <aside class="sidebar">
      {nav_html}
    </aside>
    <main class="content">
      <div class="{html.escape(page_grid_class)}">
        <div class="page-main">
          {content_html}
        </div>
        <aside class="margin-notes" id="margin-notes" aria-label="Notes marginales"></aside>
      </div>
    </main>
  </div>
  <script src="assets/app.js"></script>
</body>
</html>
'''
