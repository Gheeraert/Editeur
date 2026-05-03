# Note de cadrage
## Projet : chaîne modulaire de préparation éditoriale assistée pour les PURH

## 1. Contexte

Les Presses universitaires de Rouen et du Havre souhaitent se doter d'un environnement de travail permettant d'assister la correction de copie et la préparation éditoriale des manuscrits, dans une logique à la fois rigoureuse, sobre et modulaire.

Le projet ne consiste pas seulement à automatiser certaines vérifications formelles. Il vise à construire une chaîne capable d'accompagner la transformation progressive d'un manuscrit d'auteur vers un texte structuré, stylé, contrôlable et exploitable dans des formats savants.

Le développement sera conduit avec l'appui de Codex AI, selon une méthode modulaire, incrémentale et documentée.

---

## 2. Finalité du projet

L'objectif est de constituer, pour les PURH, une chaîne de préparation éditoriale modulaire permettant :

- de contrôler la conformité orthotypographique d'un manuscrit ;
- de signaler des incohérences ou anomalies éditoriales ;
- de proposer, avec prudence, des suggestions d'amélioration stylistique ;
- de préparer l'intégration du texte dans une chaîne de structuration compatible avec Métopes ;
- de produire un pivot Python‑JSON stable ;
- d'exporter ce pivot vers DOCX, XML‑TEI, LaTeX, HTML ou PDF ;
- de conserver la trace des décisions prises.

---

## 3. Principe structurant : le pivot Python‑JSON

Le cœur du projet est le pivot Python‑JSON.

```text
Python dataclasses  <=>  JSON canonique
```

Le modèle Python permet le traitement interne. Le JSON canonique permet la vérification, la comparaison, les fixtures, la traçabilité et le dialogue entre modules.

Les sorties ne doivent pas gouverner le modèle. Elles doivent le représenter.

```text
DOCX, XML‑TEI, LaTeX, HTML et PDF = projections du pivot
```

---

## 4. Principes directeurs

### 4.1 Modularité

Chaque brique fonctionnelle doit pouvoir être développée, testée, documentée et, au besoin, remplacée indépendamment des autres.

### 4.2 Interopérabilité

Les modules doivent dialoguer dans un cadre commun, au moyen du pivot Python‑JSON et de diagnostics structurés.

### 4.3 Prudence éditoriale

L'automatisation ne doit jamais effacer le rôle de validation humaine. Le système doit distinguer nettement :

- ce qui relève d'une règle vérifiable ;
- ce qui relève d'une suggestion interprétative ;
- ce qui relève d'une décision éditoriale humaine ;
- ce qui doit être seulement diagnostiqué.

### 4.4 Traçabilité

Toute intervention automatique ou semi-automatique doit pouvoir être identifiée, justifiée, relue et, si nécessaire, annulée.

### 4.5 Sobriété technique

Le projet doit privilégier des solutions simples, maintenables, pérennes et bien documentées, plutôt que des dispositifs lourds ou opaques.

### 4.6 Refus des patches de sortie

Un exporteur ne doit pas réparer silencieusement un pivot incomplet. S'il manque une décision structurelle, il faut corriger l'amont ou produire un diagnostic.

---

## 5. Périmètre fonctionnel envisagé

### 5.1 Module de contrôle orthotypographique

Ce module, fondé sur des règles explicites, aura pour fonction de vérifier la conformité du manuscrit à un ensemble de normes définies par les PURH.

Il pourra couvrir : ponctuation, espaces fines et insécables, guillemets, capitales et petites capitales, italiques, appels de notes, régularités bibliographiques, titres, intertitres, numérotations et éléments paratextuels.

### 5.2 Module d'analyse stylistique assistée par IA

Ce module exploitera une API d'intelligence artificielle pour repérer, de manière prudente : lourdeurs, répétitions, ambiguïtés, formulations maladroites, tensions ponctuelles de registre ou de cohérence rédactionnelle.

Les résultats devront être produits sous forme de suggestions, jamais comme des réécritures imposées.

### 5.3 Module de décision structurelle

Ce module transforme des faits documentaires en décisions prudentes : titres, citations, vers, tableaux, listes, bibliographie, code, transcriptions.

Il doit produire scores, diagnostics, vetos et transformations traçables.

### 5.4 Module de canonicalisation du pivot

Ce module inscrit les décisions retenues dans une représentation stable.

Exemple : une séquence de vers reconnue ne doit pas seulement être « jolie » dans le DOCX ; elle doit devenir, dans le pivot :

```text
quote_block + quote_kind=poetry + lineation=verse + lignes exploitables
```

### 5.5 Module de validation du pivot

Ce module vérifie les invariants avant export.

Exemples :

- un heading possède un niveau ;
- une citation en vers possède des lignes ;
- une table n'est pas aplatie silencieusement ;
- une zone protégée ne reste pas une structure incomplète.

### 5.6 Module d'export Métopes / TEI

Ce module produit un XML compatible avec le périmètre Métopes retenu, depuis le pivot validé.

Il ne doit pas redétecter les structures.

### 5.7 Module de visualisation HTML/PDF/LaTeX

Ces modules produisent des représentations de lecture, de contrôle ou de publication.

Ils peuvent révéler une erreur du pivot, mais ne doivent pas devenir des sources de vérité.

---

## 6. Méthode de développement

Le développement repose sur :

- découpage fonctionnel fin ;
- branches propres pour les refactorisations conceptuelles ;
- tests unitaires ;
- fixtures représentatives ;
- tests du pivot ;
- documentation immédiate des conventions ;
- validation régulière sur corpus réels ;
- usage de Codex AI comme assistant encadré.

Codex AI intervient non comme substitut au pilotage du projet, mais comme outil de production modulaire, dans un cadre spécifié avec précision : objectifs courts, périmètres clairs, sorties testables, révision humaine systématique.

---

## 7. Livrables attendus

À terme, le projet devra produire :

- un ensemble de modules Python autonomes ;
- une documentation fonctionnelle et technique ;
- un contrat de pivot Python‑JSON ;
- un corpus de tests et de fixtures ;
- des exemples d'entrée et de sortie ;
- des exports DOCX, XML‑TEI, LaTeX, HTML et PDF fondés sur le pivot ;
- éventuellement une interface légère d'orchestration ou de pilotage.

---

## 8. Bénéfices attendus

Le projet vise plusieurs gains :

- amélioration de la qualité formelle des manuscrits ;
- homogénéisation des pratiques éditoriales ;
- gain de temps dans les vérifications répétitives ;
- meilleure explicitation des normes internes ;
- meilleure continuité entre correction, structuration et publication ;
- réutilisabilité des modules dans d'autres contextes éditoriaux ;
- capitalisation progressive d'un savoir-faire éditorial numérique propre aux PURH.

---

## 9. Points de vigilance

Plusieurs risques doivent être anticipés :

- confusion entre correction normative et suggestion stylistique ;
- confusion entre style Word et structure éditoriale ;
- confusion entre zone protégée et structure canonique ;
- multiplication de patches locaux dans les exporteurs ;
- dépendance à des gros documents réels au lieu de fixtures courtes ;
- usage excessif de l'IA ;
- absence de round‑trip JSON ;
- absence de tests de cohérence entre DOCX, XML et LaTeX.

---

## 10. Formule de synthèse

```text
L'amont décide.
Le pivot stabilise.
L'aval représente.
```
