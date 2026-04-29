# Règles Typographiques PURH (V1 opérationnelle)

## 1. Objet

Ce document transforme les consignes éditoriales disponibles en règles exploitables pour le développement.

Priorité de cette version :
- correction orthotypographique prudente ;
- assistance à la relecture ;
- traçabilité ;
- limitation des faux positifs.

Ce document ne vise pas l’exhaustivité du *Lexique des règles typographiques* de l’Imprimerie nationale.

## 2. Sources lues

### Sources PURH attestées
- `sources/editorial_rules/CONSIGNES_AUTEURS_PURH_2025 (1).pdf` (extraction de travail : `out/analysis_CONSIGNES_AUTEURS_PURH_2025.txt`)

### Sources typographiques générales
- `sources/editorial_rules/Lexique des règles typographiques en usage à lImprimerie nationale.epub`
- `C:/Users/Blais/Desktop/Lexique des règles typographiques en usage à lImprimerie nationale (...).epub` (même contenu, hash identique après extraction)
- extraction de travail : `out/analysis_Lexique_des_r_gles_typographiques_en_usage_lImprimerie_nationale.txt`

### Sources de gouvernance projet
- `AGENTS.md`
- `docs/EDITORIAL_PIPELINE.md`
- `AI_STYLE_POLICY.md`

## 3. Niveaux d’automatisation

- `A1` Auto-correction sûre : règle locale, déterministe, peu ambiguë.
- `A2` Suggestion localisée : proposition ciblée, validation humaine requise.
- `A3` Diagnostic seulement : signalement sans modification automatique.
- `A4` Hors périmètre initial : à traiter plus tard ou manuellement.

## 4. Familles de règles (20–30 règles prioritaires)

Le catalogue détaillé est dans `docs/RULES_CATALOG.md`.
Cette section résume les familles demandées et les IDs prioritaires.

### 4.1 Espaces et ponctuation
- `R-SP-001` espace fine insécable avant `: ; ? !` (`A1`)
- `R-SP-002` suppression espace avant `, .` (`A1`)
- `R-SP-003` réduction des doubles espaces (`A1`)
- `R-SP-004` séparateur des milliers en espace fine insécable (`A1`)

### 4.2 Guillemets
- `R-GQ-001` guillemets français pour texte français (`A1`)
- `R-GQ-002` espaces insécables à l’intérieur de `« »` (`A1`)
- `R-GQ-003` guillemets anglais pour citation de second niveau (`A3`)
- `R-GQ-004` position ponctuation / guillemet fermant selon type de citation (`A3`)

### 4.3 Appels de note
- `R-AN-001` appel en exposant arabe (`A3`)
- `R-AN-002` appel avant ponctuation et avant guillemet fermant (`A2/A3`)
- `R-AN-003` appel non précédé d’espace, non rejeté en début de ligne (`A3`)

### 4.4 Notes de bas de page
- `R-FN-001` notes en bas de page (pas fin de volume, sauf exception éditoriale) (`A3`)
- `R-FN-002` une note = un seul paragraphe (`A3`)
- `R-FN-003` abréviations latines usuelles normalisées (`ibid.`, `op. cit.`, `loc. cit.`) (`A1/A2`)

### 4.5 Siècles, ordinaux, exposants
- `R-SO-001` siècles en chiffres romains + `e` (petites capitales côté mise en forme) (`A1/A2`)
- `R-SO-002` ordinaux `1re`, `5e` (pas `1ère`, `5ème`) (`A1`)
- `R-SO-003` `nᵒ`, `rᵒ`, `vᵒ` (o en exposant : diagnostic si style absent) (`A3`)

### 4.6 Abréviations courantes
- `R-AB-001` `etc.` (jamais `etc...`, jamais en italique) (`A1/A2`)
- `R-AB-002` abréviations proscrites dans le corps courant (sauf usages nécessaires) (`A3`)
- `R-AB-003` espaces insécables dans `op. cit.`, `loc. cit.`, `s. l.`, `s. d.` (`A1/A2`)
- `R-AB-004` ne pas redoubler pour le pluriel (`p.`, `v.`, `l.`) (`A2`)

### 4.7 Capitales, petites capitales, tout-majuscules
- `R-CA-001` accentuer les capitales (`A2/A3`)
- `R-CA-002` éviter `TOUT EN MAJUSCULES` (titres, index, biblio) (`A3`)
- `R-CA-003` siècles en petites capitales côté style, pas de substitution destructrice (`A3`)

### 4.8 Citations courtes et longues
- `R-CI-001` citation FR fondue : romain + guillemets (`A3`)
- `R-CI-002` citation FR non fondue : romain sans guillemets (`A3`)
- `R-CI-003` citation étrangère fondue : italique + guillemets (`A3`)
- `R-CI-004` citation étrangère non fondue : italique ; traduction en romain (`A3`)

### 4.9 Titres et hiérarchie
- `R-TI-001` hiérarchie stricte des niveaux de titre, sans saut (`A3`)
- `R-TI-002` pas de numérotation des intertitres (hors titres de parties) (`A3`)
- `R-TI-003` homogénéité de style par niveau (`A3`)

### 4.10 Bibliographie
- `R-BI-001` placement en fin de volume / fin d’article (`A3`)
- `R-BI-002` cohérence d’un seul modèle bibliographique par ouvrage (`A3`)
- `R-BI-003` tiret cadratin en remplacement auteur répété (modèle 1) (`A2/A3`)

### 4.11 Cas à ne pas automatiser
- `R-NA-001` choix de style dans citations complexes (romain/italique/gras) (`A4`)
- `R-NA-002` normalisation lourde de bibliographie hétérogène (`A4`)
- `R-NA-003` réécriture stylistique savante (`A4`, IA uniquement en suggestion)

## 5. Règles déjà couvertes par le code actuel (repérables)

### Couverture notable
- `OrthotypoService` :
  - apostrophe typographique (`purh.apostrophe`)
  - points de suspension (`purh.points_suspension`)
  - guillemets droits -> français + espaces internes (`purh.guillemets.*`)
  - espaces avant ponctuation forte/faible (`purh.espaces.*`)
  - civilités avec insécable (`purh.civilite`)
  - siècles (`purh.siecles`)
  - `etc.` (`purh.abreviations.etc`)
  - pagination / `n°` / milliers (`purh.pagination.espace`, `purh.numero`, `purh.nombres.milliers`)
  - tirets (`purh.tiret.double`, `purh.tiret.incise`)
- `FootnoteNormalizer` :
  - normalisation locale de notes (`ibid`, `op. cit.`, point final, nettoyage tête de note)
- `BibliographyNormalizer` :
  - normalisation locale (ponctuation finale, abréviations de pagination)

### Couverture partielle ou absente
- placement exact des appels de note vs ponctuation/guillemets (`R-AN-002`) ;
- gestion fiable des guillemets de second niveau (`R-GQ-003`) ;
- règles riches de citation (FR/étranger, fondue/non fondue) ;
- hiérarchie des titres fondée explicitement sur consignes PURH ;
- règles bibliographiques avancées (cohérence de modèle, tiret cadratin auteur répété).

## 6. Principes de prudence à appliquer en code

- privilégier `A1` uniquement pour transformations locales réversibles ;
- basculer en `A2`/`A3` dès qu’un contexte syntaxique ou éditorial est requis ;
- éviter toute correction silencieuse globale ;
- journaliser systématiquement les transformations ;
- en cas de doute : diagnostic.

## 7. Prochaine étape recommandée

Implémenter d’abord les tests des règles `A1` déjà couvertes et sécuriser les zones à faux positifs (`R-AN-002`, `R-GQ-004`, `R-SO-001`), avant d’ajouter de nouvelles corrections automatiques.
