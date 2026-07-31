from __future__ import annotations

import shutil
from pathlib import Path

from purh_editorial.corrector.word_document import correct_word_copy


DETERMINISTIC_RULE_IDS = (
    "purh.apostrophe",
    "purh.points_suspension",
    "purh.ligature.oe",
    "purh.guillemets.anglais_vers_chevrons",
    "purh.guillemets.espace_apres_ouvrant",
    "purh.guillemets.espace_avant_fermant",
    "purh.espaces.avant_ponct_forte",
    "purh.espaces.avant_ponct_faible",
    "purh.espaces.double",
    "purh.civilite",
    "purh.numeral_dynastique",
    "purh.siecles",
    "purh.ordinaux",
    "purh.abreviations.etc",
    "purh.pagination.espace",
    "purh.numero",
    "purh.folio",
    "purh.recto_verso",
    "purh.abreviations.redoublement",
    "purh.nombres.milliers",
    "purh.ecriture_inclusive.point_median",
    "purh.date.jour_mois",
    "purh.siecles.style",
    "purh.numero.style",
    "purh.folio.style",
    "purh.recto_verso.style",
    "purh.ordinaux.style",
    "purh.civilite.style",
    "purh.note.espace_initiale",
    "purh.note.espace_op_cit",
    "purh.note.espace_sans_lieu_date",
    "purh.note.italique_latin",
    "purh.biblio.pagination_nnbsp",
    "purh.biblio.numero_nnbsp",
    "purh.tiret.incise.diagnostic",
    "purh.note.appel.placement",
    "purh.note.appel.espace_avant",
    # Front matter (résumé/mots-clés/remerciements) : détection déterministe
    # par correspondance exacte de la ligne (structure.py), appliquée comme
    # diagnostic (surlignage turquoise) plutôt que comme transformation
    # structurelle silencieuse — la cible Word exacte (style à appliquer)
    # n'est pas spécifiée par le catalogue et ne doit pas être devinée.
    "structure.frontmatter.abstract",
    "structure.frontmatter.keywords",
    "structure.frontmatter.acknowledgment",
    # Titre tout capitales : condition déterministe (style Word de titre +
    # texte tout capitales, `is_allcaps_heading` dans structure.py),
    # appliquée comme diagnostic (surlignage turquoise) et non comme
    # transformation automatique — ramener silencieusement à la casse
    # phrase perdrait la casse d'un nom propre éventuellement présent dans
    # le titre. Confirmé sur deux corpus indépendants (voir
    # docs/journal/ANALYSE_CORPUS_HP2.md et
    # docs/journal/OBSERVATIONS_CORPUS_2026-07-31.md).
    "structure.allcaps.heading",
    # Mise en forme minimale PURH des styles Word natifs (branche "stylage") :
    # modifie la definition des styles eux-memes (Font/ParagraphFormat), pas
    # un formatage direct paragraphe par paragraphe - voir rules/styling.py.
    # Condition deterministe : Style.BuiltIn (jamais un style personnalise
    # portant le meme nom).
    "purh.style.titre",
    "purh.style.citation",
    "purh.style.citation_intense",
    "purh.style.normal",
    "purh.style.corps_de_texte",
    "purh.style.note_bas_de_page",
    "purh.style.appel_de_note",
    # Reapplication silencieuse du style "Normal" sur chaque paragraphe qui
    # le porte deja (branche "heuristique") : contourne un artefact de
    # rendu Word observe par l'editrice (paragraphes deja en "Normal" mal
    # affiches tant que le style n'est pas reapplique explicitement). Aucune
    # modification de texte, condition deterministe (style Word natif) - voir
    # _reapply_normal_style dans word_document.py.
    "purh.style.normal_refresh",
    # Fusion des citations poetiques (branche "heuristique") : bloc de
    # paragraphes consecutifs portant le style natif "Citation intense"
    # (rules/styling.py) fusionne en un seul paragraphe, chaque vers separe
    # du suivant par un saut de ligne manuel plutot qu'une fin de paragraphe.
    # Condition deterministe (style Word natif), pas le moteur de score
    # legacy `poetry` que docs/REBORN_ARCHITECTURE.md §7 exclut - voir
    # _apply_poetry_merge dans word_document.py.
    "structure.poetry.heuristique",
)

HEURISTIC_RULE_IDS = (
    "purh.guillemets.droits",
    "purh.tiret.double",
    "purh.guillemets.ponctuation_fermante",
    "purh.note.majuscule_initiale",
    "purh.note.abreviation_latine",
    "purh.note.ponctuation_finale",
    "purh.note.diagnostic.debut_minuscule",
    "purh.note.diagnostic.ponctuation_finale_ambigue",
    # Bibliographie : la section est repérée par le style de titre Word
    # (Titre 1-4 / Heading 1-4) associé au titre de section reconnu
    # (Bibliographie, Sources, Références bibliographiques...) — condition
    # explicite et déterministe, pas un score. Voir
    # `_apply_bibliography_entry` / `BIBLIOGRAPHY_SECTION_HEADING_RE` dans
    # word_document.py / rules/bibliography.py.
    "purh.biblio.ponctuation_finale",
    "purh.biblio.casse_auteur",
)

# Règles du catalogue (docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md) volontairement
# absentes de RULE_IDS : le catalogue les marque lui-même comme `planned`
# (jamais fonctionnelles, même dans la voie legacy) ou `dormant`/`disabled`
# (bibliography.entry.detect, structure.lineated.short_sequence.merge), ou
# reposent sur le moteur de score/seuil de la voie legacy (`structure_service`,
# score `heading`/`poetry`/`quote_structure`/`bibliography_structure`) que le
# nouveau chemin d'exécution exclut explicitement
# (docs/REBORN_ARCHITECTURE.md §7). Les concevoir sans scoring demande de
# spécifier, règle par règle, la condition de déclenchement exacte et l'action
# Word résultante — un vrai travail éditorial, pas une simple portation.
#
# "purh.tiret.incise" y figure aussi : le catalogue la marque `disabled`
# (jamais fonctionnelle) et aucun détecteur ne l'implémente dans
# corrector/rules/ — elle ne doit pas apparaître dans RULE_IDS tant qu'elle
# n'a pas de détecteur réel, pour la même raison que les règles ci-dessus.
NOT_YET_IMPLEMENTED_RULE_IDS = (
    "structure.frontmatter.circuit_breaker",
    "structure.bibliography.section.start",
    "structure.bibliography.section.end",
    "structure.bibliography.item.promote",
    "bibliography.entry.detect",
    "purh.tiret.incise",
    "structure.source_style.heading",
    "structure.bold.heading",
    "structure.italic.author",
    "structure.italic.heading",
    "structure.epigraph.heuristic",
    "structure.bibliography.section",
    "structure.bibliography.heuristic",
    "structure.indent.quote",
    "structure.quote.guillemets",
    "structure.heading.heuristic",
    "structure.heading.diagnostic",
    "structure.lineated.blank_bounded.merge",
    "structure.lineated.short_sequence.merge",
    "structure.lineated.group.annotate",
    "structure.lineated.stanza.merge",
)

RULE_IDS = DETERMINISTIC_RULE_IDS + HEURISTIC_RULE_IDS


def correct_docx(input_path: Path, output_path: Path) -> dict[str, int]:
    source = Path(input_path)
    destination = Path(output_path)

    if not source.is_file():
        raise FileNotFoundError(f"Document d'entrée introuvable : {source}")
    if source.suffix.lower() != ".docx":
        raise ValueError("Le document d'entrée doit porter l'extension .docx.")

    source_resolved = source.resolve()
    destination_resolved = destination.resolve()
    if source_resolved == destination_resolved:
        raise ValueError("Les chemins d'entrée et de sortie doivent être différents.")
    if destination.exists():
        raise FileExistsError(f"Le fichier de sortie existe déjà : {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return correct_word_copy(destination_resolved, RULE_IDS)
