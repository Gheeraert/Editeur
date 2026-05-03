# AGENTS.md

## 1. Rôle de ce fichier

Ce document fixe les règles de travail pour l'assistant de développement utilisé sur ce projet, notamment Codex AI.

Le projet concerne une chaîne modulaire de préparation éditoriale pour les PURH. Le développement doit rester strictement encadré, modulaire, testable, traçable et prudent sur le plan éditorial.

---

## 2. Principes impératifs

### 2.1 Pas de monolithe

Ne jamais concentrer des responsabilités hétérogènes dans un gros script unique. Séparer modèle de données, logique métier, lecture/écriture, sérialisation JSON, appels IA, rendu, CLI ou interface.

### 2.2 Développement incrémental, refactorisation assumée si nécessaire

Toute demande ordinaire doit être traitée par petits périmètres : une fonction, un module, un mapping, une famille de tests, une règle éditoriale isolée ou une fixture ciblée.

Cependant, si le contrat de données est incohérent ou si plusieurs modules produisent des interprétations concurrentes, il faut préférer une branche de refactorisation propre à une accumulation de patches locaux.

Dans ce cas :

- documenter l'invariant visé avant de coder ;
- créer ou modifier les tests du pivot ;
- supprimer les heuristiques locales concurrentes ;
- adapter ensuite les sorties ;
- ne pas masquer le problème par un rendu opportuniste.

### 2.3 Tests obligatoires

Toute évolution significative doit s'accompagner de tests : tests unitaires, tests du pivot, fixtures minimales, absence de régression sur les cas stabilisés.

Un cas réel volumineux doit être réduit en fixture courte avant d'être utilisé comme garde-fou durable.

### 2.4 Aucune invention normative silencieuse

Ne pas inventer de règles PURH. Lorsqu'une norme locale n'est pas documentée : expliciter l'hypothèse, isoler la règle, la marquer comme provisoire, préférer un comportement conservateur et produire un diagnostic plutôt qu'une transformation automatique.

### 2.5 Prudence maximale pour l'IA stylistique

Le module IA ne doit jamais réécrire massivement, uniformiser abusivement, modifier silencieusement le texte source, confondre préférence stylistique et faute, transformer une citation ou intervenir dans une zone protégée sans règle explicite.

Les suggestions doivent rester locales, motivées, révisables et optionnelles.

### 2.6 Préserver la traçabilité

Toute transformation doit pouvoir être identifiée, journalisée, expliquée, testée et annulée. Une transformation sans `rule_id`, diagnostic ou justification est suspecte.

### 2.7 Préférer la lisibilité à l'astuce

Le code attendu doit être clair, typé si possible, modulaire, documenté et sans magie inutile.

### 2.8 Refuser les dépendances lourdes sans justification

Ne pas ajouter de dépendance importante sans raison claire. Privilégier la standard library, les bibliothèques déjà présentes et les bibliothèques stables.

---

## 3. Représentation des données

Le cœur du projet doit utiliser des dataclasses Python.

Le JSON sert à sérialiser le pivot, fabriquer les fixtures, échanger entre modules si nécessaire, déboguer, comparer et tracer.

Le JSON n'est pas un export de confort : il doit devenir une représentation stable, versionnée et relisible du pivot.

Ne pas bâtir le cœur métier sur des dictionnaires non typés si une dataclass claire est préférable.

---

## 4. Modèle de décision éditoriale

Avant toute tâche touchant à la structuration, lire :

```text
docs/EDITORIAL_DECISION_MODEL.md
docs/PIVOT_JSON_CONTRACT.md
docs/EXPORTERS_CONTRACT.md
```

Principe fondamental :

```text
un fait Word n'est pas une structure éditoriale
```

Principe complémentaire :

```text
un exporteur ne doit pas inventer une structure absente du pivot
```

Un style Word, une puce, un retrait ou un gras sont des indices. Ils doivent être confrontés à d'autres indices.

Le pipeline doit distinguer : faits documentaires, indices, candidats, conflits, vetos, décision, canonicalisation, validation du pivot, export.

---

## 5. IA : hiérarchie d'usage

Ordre de préférence : déterministe, heuristique scorée, IA locale encadrée, IA exploratoire ou freestyle.

L'IA locale sert uniquement à arbitrer une zone grise explicitement définie. L'IA exploratoire est une solution de dernier recours et ne doit pas produire de transformation automatique.

Ne jamais utiliser l'IA pour remplacer une règle déterministe, une fixture manquante ou un invariant du pivot.

---

## 6. Zones protégées

Certaines zones doivent bloquer les transformations ordinaires : poésie, citation ancienne, code informatique, transcription linguistique, tableau, formule, bibliographie, légende.

Lorsqu'une zone protégée est détectée, ne pas appliquer aveuglément : promotion en titre, correction typographique agressive, suggestion stylistique, normalisation d'espaces ou de ponctuation.

Exemple critique : un vers dans une séquence poétique ne doit pas devenir un heading, même s'il est court, commence par une majuscule ou possède un style Word de titre.

Important : une zone protégée n'est pas une sémantique complète. Elle doit conduire à une canonicalisation explicite si elle détermine la structure du bloc.

---

## 7. Exporteurs

Les exporteurs DOCX, XML‑TEI, LaTeX, HTML ou PDF ne doivent pas contenir de logique de reconnaissance structurelle.

Ils doivent :

- consommer le pivot validé ;
- représenter les types canoniques ;
- produire un diagnostic si le pivot est incohérent ;
- éviter toute réparation silencieuse.

Ils ne doivent pas :

- décider localement qu'un bloc est un titre, un vers ou une liste ;
- utiliser un style Word source comme vérité structurelle ;
- masquer une erreur du pivot par un rendu opportuniste.

---

## 8. Méthode de livraison attendue

Pour toute tâche de développement, fournir : fichiers modifiés/créés, choix d'architecture, limites connues, tests ajoutés, tests exécutés, ce qui reste volontairement hors périmètre.

Pour toute tâche touchant les exports, préciser aussi :

- quel invariant du pivot est consommé ;
- quels tests de pivot ont été exécutés ;
- si l'exporteur contient encore une heuristique locale à supprimer.

---

## 9. Ce qu'il faut faire avant de coder

Toujours vérifier :

- quel document de cadrage gouverne la tâche ;
- quelles fixtures existent déjà ;
- quel comportement attendu est vérifiable ;
- si le cas relève d'une règle déterministe, d'une heuristique, d'une zone grise ou d'une suggestion IA ;
- si une zone protégée doit être posée avant transformation ;
- si la décision doit être canonicalisée dans le pivot ;
- si l'export attendu représente déjà un état pivot valide.

---

## 10. Ce qu'il faut éviter

- implémentations globales sans tests ;
- fusion de plusieurs responsabilités ;
- modifications massives « pour harmoniser » hors branche de refactorisation ;
- appels à une IA sans encadrement ;
- normalisation silencieuse ;
- dépendance à des comportements implicites ;
- parsing fragile si un modèle plus robuste est possible ;
- transformation structurelle fondée sur un seul indice Word ;
- patches locaux dans les exporteurs pour compenser un pivot incomplet.

---

## 11. Règle d'or

Quand une décision oppose sophistication et clarté, automatisation et contrôle humain, puissance et traçabilité, IA et règle explicite, choisir clarté, contrôle humain, traçabilité et règle explicite si elle existe.

Quand une sortie fonctionne mais que le pivot est incohérent, corriger le pivot.

---

## 12. Gouvernance pipeline

Pour toute tâche touchant au pipeline éditorial, les documents prioritaires sont :

```text
docs/PIVOT_JSON_CONTRACT.md
docs/EXPORTERS_CONTRACT.md
docs/EDITORIAL_DECISION_MODEL.md
docs/EDITORIAL_PIPELINE.md
ARCHITECTURE.md
DATA_MODEL.md
SPECS.md
```

Rappel : la sortie de production visée est l'XML‑TEI Métopes ; le DOCX reste une sortie de relecture humaine ; l'IA reste optionnelle et encadrée ; le JSON pivot sert de contrat de développement et de test.
