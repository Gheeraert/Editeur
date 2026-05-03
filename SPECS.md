# Spécifications fonctionnelles

## 1. Objet

Le projet vise à construire une chaîne modulaire de préparation éditoriale pour les PURH.

Cette chaîne doit permettre :

- de contrôler un manuscrit sur le plan orthotypographique ;
- de produire des diagnostics structurés ;
- d'offrir des suggestions stylistiques prudentes ;
- de préparer le texte à une structuration Métopes / XML ;
- de produire un pivot Python‑JSON stable ;
- d'exporter ce pivot vers DOCX, XML‑TEI, LaTeX, HTML ou PDF ;
- de documenter les décisions éditoriales prises par le système.

---

## 2. Finalité

Le système n'a pas pour but de remplacer l'éditrice ou l'éditeur.

Il a pour but :

- d'automatiser ce qui relève de règles explicites ;
- d'assister ce qui relève d'un jugement prudent ;
- de rendre plus fluide le passage du manuscrit vers une forme structurée et publiable ;
- de rendre visibles les conflits d'interprétation documentaire ;
- de stabiliser un modèle pivot réutilisable ;
- de préserver la validation humaine.

Le système doit distinguer : diagnostic, suggestion, correction locale proposée, transformation structurelle, canonicalisation du pivot, export et validation humaine.

---

## 3. Principe de décision éditoriale

Un document source ne fournit pas immédiatement une structure éditoriale. Il fournit des faits : style Word, mise en forme, indentation, puces, tableaux, notes, objets, fragments textuels.

Ces faits deviennent des indices. Les indices produisent des candidats. Les candidats peuvent entrer en conflit.

Exemple :

```text
bloc court + majuscule initiale + style Titre 2
  -> candidat titre

mais :
  séquence de lignes courtes + ponctuation de vers + homogénéité de longueur
  -> candidat poésie

décision :
  protéger la séquence poétique
  ne pas promouvoir le vers isolé en titre
  canonicaliser en citation en vers si le score le permet
```

Cette doctrine est définie dans `docs/EDITORIAL_DECISION_MODEL.md`.

---

## 4. Principe du pivot

Le pivot Python‑JSON est la source de vérité du pipeline.

```text
Python dataclasses  <=>  JSON canonique
```

Les exports ne doivent pas compenser un pivot incomplet. Ils ne doivent faire que représenter l'état canonicalisé.

Objectif :

```text
un même pivot doit produire des sorties cohérentes : DOCX, XML‑TEI, LaTeX.
```

---

## 5. Modules fonctionnels

### 5.1 Module A — Ingestion et normalisation initiale

Rôle : recevoir un document source et produire une représentation interne exploitable.

Entrées : DOCX, TXT, XML, ou autres formats via conversion en amont.

Sorties : `Document` interne, journal d'ingestion, diagnostics de lecture, conservation des faits matériels utiles.

Hors périmètre actuel : import exhaustif de tous les objets Word complexes, conversion universelle parfaite, interprétation immédiate de tous les styles Word comme structures éditoriales.

### 5.2 Module B — Contrôle orthotypographique

Rôle : détecter des anomalies ou écarts à des règles formelles explicites.

Exemples : espaces avant `: ; ? !`, guillemets, appels de note, italiques, siècles, dates, doubles espaces, abréviations.

Règle : aucune correction silencieuse. Toute correction doit être localisée, explicable, désactivable, réversible et testée.

Le module doit respecter les zones protégées : code, transcription linguistique, citation ancienne, poésie, tableau, formule, bibliographie spécialisée.

### 5.3 Module C — Suggestions stylistiques assistées par IA

Rôle : repérer localement des formulations perfectibles.

L'IA stylistique ne produit pas une réécriture du livre. Elle ne doit pas lisser la voix de l'auteur, imposer un registre, corriger des choix savants non fautifs ou transformer automatiquement le texte source.

### 5.4 Module D — Reconnaissance / préparation de structures

Rôle : identifier ou normaliser des structures utiles à la conversion Métopes / XML.

Structures potentielles : titre, sous-titre, intertitre, paragraphe, note, citation en bloc, épigraphe, liste, bibliographie, annexe, tableau, code, transcription linguistique, poésie, légende.

Règle d'ordre : les zones protégées doivent être repérées avant les promotions structurelles concurrentes. Une séquence poétique doit bloquer la promotion d'un vers en titre.

### 5.5 Module E — Canonicalisation et validation du pivot

Rôle : transformer les décisions en représentation stable et vérifier les invariants.

Exemples :

- une citation en vers reçoit `quote_kind=poetry`, `lineation=verse` et des lignes exploitables ;
- un titre reçoit un `heading_level` cohérent ;
- une table conserve un modèle tabulaire ou un OOXML protégé ;
- une zone protégée ne reste pas un simple attribut flottant si elle implique une structure.

Sorties : pivot Python‑JSON validé, diagnostics d'incohérence, éventuellement blocage d'export de production.

### 5.6 Module F — Passage vers un XML de travail compatible Métopes

Rôle : produire, enrichir ou contrôler une représentation XML conforme au périmètre retenu.

Les mappings réels devront être fondés sur des exemples XML réels, les usages Métopes retenus, les pratiques PURH et des fixtures ciblées.

Le XML est produit depuis le pivot validé. Il ne doit pas redétecter localement les structures.

### 5.7 Module G — Visualisation XML / HTML / PDF / LaTeX

Rôle : transformer le pivot ou le XML validé en rendus lisibles pour vérification, circulation interne, publication de travail et contrôle de structure.

Un mauvais rendu est souvent le symptôme d'une décision structurelle mal posée. La première vérification doit porter sur le pivot.

---

## 6. Régimes d'action

- Diagnostic : signalement d'un point à examiner.
- Suggestion : proposition facultative, non imposée.
- Correction locale proposée : transformation déterministe possible sur règle explicite.
- Transformation structurelle : modification du type ou des attributs d'un bloc, seulement si les règles et vetos le permettent.
- Canonicalisation : inscription stable de la décision dans le pivot.
- Validation humaine : décision finale d'acceptation, de rejet ou de correction.
- Export : représentation du pivot dans un format cible.

---

## 7. Pipeline cible

1. ingestion ;
2. extraction des faits documentaires ;
3. identification des zones protégées ;
4. normalisation minimale ;
5. contrôle orthotypographique ;
6. reconnaissance / préparation structurelle ;
7. suggestions stylistiques prudentes ;
8. canonicalisation du pivot ;
9. validation des invariants Python‑JSON ;
10. production JSON canonique ;
11. exports DOCX, XML‑TEI, LaTeX, HTML/PDF.

L'architecture doit permettre l'exécution d'un seul module, la réutilisation indépendante de certains modules, le saut volontaire d'étapes et la désactivation complète de l'IA.

---

## 8. Formats et échanges

- Modèle interne : dataclasses Python.
- Format pivot sérialisé : JSON documenté, versionné, relisible.
- Journalisation : diagnostics, suggestions, transformations, décisions, vetos, scores et métadonnées de traitement.
- Exports : vues spécialisées du pivot.

---

## 9. Critères de réussite

Le projet sera satisfaisant si :

- le pivot Python‑JSON est stable et relisible ;
- les règles orthotypographiques sont testées ;
- les suggestions IA restent prudentes ;
- l'IA sait s'abstenir ;
- les zones protégées empêchent les faux positifs destructeurs ;
- le passage vers XML est intelligible ;
- les exports ne contiennent plus d'heuristiques structurelles concurrentes ;
- un même pivot produit des sorties cohérentes ;
- les cas réels PURH peuvent être intégrés sans refonte brutale.

---

## 10. Hors périmètre provisoire

Ne pas inclure d'emblée : correction grammaticale massive, réécriture complète, gestion exhaustive de tous les objets Word complexes, PAO complète, import automatisé InDesign, IA freestyle activée par défaut, transformation automatique de cas interprétatifs non testés.

Ne pas résoudre les incohérences du pivot par des patches locaux dans les exporteurs.

---

## 11. Dépendances documentaires nécessaires

Guide typographique PURH, couples manuscrit auteur / manuscrit stylé, exemples XML Métopes réels, rendus HTML/PDF, exemples de cas ambigus, éventuellement CSL bibliographique.
