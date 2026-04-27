# Projet PURH — chaîne modulaire de préparation éditoriale assistée

## Objet

Ce dépôt vise à préparer une chaîne modulaire de traitement éditorial pour les Presses universitaires de Rouen et du Havre (PURH).

Le projet a pour finalité d'assister plusieurs étapes de la préparation d'un manuscrit :

1. **contrôle orthotypographique déterministe** ;
2. **analyse stylistique prudente assistée par IA** ;
3. **préparation à la structuration Métopes / XML-TEI** ;
4. **transformation d'un XML Métopes en visualisations HTML et PDF**.

L'ensemble doit rester **modulaire**, **testable**, **documenté** et **interopérable**.

---

## Principe général

Le projet n'est pas conçu comme un monolithe, mais comme un ensemble de modules autonomes pouvant être enchaînés dans un cadre commun.

La logique cible est la suivante :

- **dataclasses Python** pour le modèle métier interne ;
- **JSON** pour les échanges, les fixtures, les états intermédiaires et le débogage ;
- **tests unitaires** et **tests d'intégration** systématiques ;
- usage de **Codex AI** comme assistant de développement encadré, jamais comme auteur autonome d'un système opaque.

---

## Modules visés

### 1. Orthotypographie
Contrôles fondés sur des règles explicites, traçables et reproductibles.

Exemples de sujets potentiels :
- espaces insécables et fines ;
- ponctuation ;
- guillemets ;
- appels de note ;
- italiques ;
- siècles, dates, abréviations ;
- cohérences de surface.

### 2. Style assisté par IA
Suggestions prudentes, non prescriptives, révisables humainement.

Exemples :
- répétitions ;
- lourdeurs ;
- ambiguïtés ;
- maladresses locales ;
- tension de registre.

### 3. Préparation Métopes / TEI
Reconnaissance ou normalisation de structures du manuscrit en vue d'une conversion vers un XML de travail compatible avec le cadre retenu.

### 4. Visualisation XML vers HTML / PDF
Module réutilisable, déjà amorcé dans un autre projet, destiné à produire des sorties lisibles, contrôlables, puis potentiellement publiables.

---

## État documentaire actuel

Les présents fichiers constituent un **socle de cadrage**.

Ils fixent :
- le périmètre ;
- l'architecture cible ;
- le modèle de données ;
- la politique de suggestions IA ;
- la stratégie de fixtures et de tests ;
- la méthode de développement avec Codex.

Ils ne remplacent pas encore :
- le guide typographique PURH réel ;
- les mappings Métopes réels ;
- les exemples XML réels ;
- les couples manuscrit auteur / manuscrit stylé ;
- les rendus HTML/PDF de référence.

Ces matériaux devront être ajoutés dans `sources/` et convertis en cas ciblés dans `fixtures/`.

---

## Arborescence proposée

```text
.
├── README.md
├── AGENTS.md
├── SPECS.md
├── ARCHITECTURE.md
├── DATA_MODEL.md
├── TYPO_RULES_PURH.md
├── AI_STYLE_POLICY.md
├── METOPES_MAPPING.md
├── FIXTURES.md
├── TEST_STRATEGY.md
├── NOTE_DE_CADRAGE.md
├── sources/
│   ├── editorial_rules/
│   ├── manuscripts_raw/
│   ├── manuscripts_styled/
│   ├── xml_samples/
│   ├── output_samples/
│   └── layout_reference/
└── fixtures/
    ├── orthotypography/
    ├── author_vs_styled/
    ├── style_suggestions/
    ├── structure_recognition/
    ├── metopes_xml/
    ├── rendering_html/
    ├── rendering_pdf/
    └── bibliography/
```

---

## Ordre de travail recommandé

1. Stabiliser la documentation.
2. Déposer un petit noyau de sources réelles.
3. Extraire les premières fixtures ciblées.
4. Définir le modèle Python minimal.
5. Développer le module orthotypographique sur cas simples.
6. Développer le cadre de suggestions stylistiques.
7. Formaliser le passage vers Métopes / XML.
8. Réintégrer le module XML → HTML/PDF.
9. Consolider tests et non-régression.

---

## Premiers matériaux à fournir

Priorité absolue :

1. guide typographique PURH ou feuille de style équivalente ;
2. deux couples **manuscrit auteur / manuscrit stylé** ;
3. deux fichiers XML Métopes réels ;
4. un ou deux rendus HTML/PDF correspondants.

---

## Convention de langue

La documentation du projet est rédigée en français.
Les noms de classes, fonctions, modules et structures de tests peuvent être en anglais si cela facilite la lisibilité du code, à condition que la terminologie métier soit documentée.

---

## Limites actuelles

Ce dépôt documentaire ne contient pas encore les normes PURH réelles ni les mappings XML définitifs.
Les sections correspondantes servent donc de **gabarits structurants** à compléter dès réception des sources.

---

## Usage avec Codex

Avant de demander une implémentation, toujours vérifier que :
- le périmètre demandé est petit ;
- les entrées / sorties sont explicites ;
- les fixtures existent ;
- le comportement attendu est testable ;
- les sections concernées de `SPECS.md`, `DATA_MODEL.md` et `TEST_STRATEGY.md` ont été relues.

Ne pas demander à Codex de "faire tout le pipeline".
Découper par modules, sous-modules, cas limites et tests.
