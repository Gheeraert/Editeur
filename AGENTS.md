# AGENTS.md

## 1. Rôle de ce fichier

Ce document fixe les règles de travail pour l'assistant de développement utilisé sur ce projet, notamment Codex AI.

Le projet concerne une chaîne modulaire de préparation éditoriale pour les PURH. Le développement doit rester strictement encadré, modulaire, testable, traçable et prudent sur le plan éditorial.

---

## 2. Principes impératifs

### 2.1 Pas de monolithe

Ne jamais concentrer des responsabilités hétérogènes dans un gros script unique. Séparer modèle de données, logique métier, lecture/écriture, sérialisation JSON, appels IA, rendu, CLI ou interface.

### 2.2 Développement incrémental

Toute demande doit être traitée par petits périmètres : une fonction, un module, un mapping, une famille de tests, une règle éditoriale isolée ou une fixture ciblée.

Éviter les refontes globales tant qu'un comportement local n'est pas stabilisé.

### 2.3 Tests obligatoires

Toute évolution significative doit s'accompagner de tests : tests unitaires, fixtures minimales, absence de régression sur les cas stabilisés.

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

Le JSON sert à sérialiser les états, fabriquer les fixtures, échanger entre modules si nécessaire, déboguer et tracer.

Ne pas bâtir le cœur métier sur des dictionnaires non typés si une dataclass claire est préférable.

---

## 4. Modèle de décision éditoriale

Avant toute tâche touchant à la structuration, lire :

```text
docs/EDITORIAL_DECISION_MODEL.md
```

Principe fondamental :

```text
un fait Word n'est pas une structure éditoriale
```

Un style Word, une puce, un retrait ou un gras sont des indices. Ils doivent être confrontés à d'autres indices.

Le pipeline doit distinguer : faits documentaires, indices, candidats, conflits, vetos, décision, transformation éventuelle.

---

## 5. IA : hiérarchie d'usage

Ordre de préférence : déterministe, heuristique scorée, IA locale encadrée, IA exploratoire ou freestyle.

L'IA locale sert uniquement à arbitrer une zone grise explicitement définie. L'IA exploratoire est une solution de dernier recours et ne doit pas produire de transformation automatique.

Ne jamais utiliser l'IA pour remplacer une règle déterministe ou une fixture manquante.

---

## 6. Zones protégées

Certaines zones doivent bloquer les transformations ordinaires : poésie, citation ancienne, code informatique, transcription linguistique, tableau, formule, bibliographie, légende.

Lorsqu'une zone protégée est détectée, ne pas appliquer aveuglément : promotion en titre, correction typographique agressive, suggestion stylistique, normalisation d'espaces ou de ponctuation.

Exemple critique : un vers dans une séquence poétique ne doit pas devenir un heading, même s'il est court, commence par une majuscule ou possède un style Word de titre.

---

## 7. Méthode de livraison attendue

Pour toute tâche de développement, fournir : fichiers modifiés/créés, choix d'architecture, limites connues, tests ajoutés, tests exécutés, ce qui reste volontairement hors périmètre.

---

## 8. Ce qu'il faut faire avant de coder

Toujours vérifier quel document de cadrage gouverne la tâche, quelles fixtures existent déjà, quel comportement attendu est vérifiable, si le cas relève d'une règle déterministe, d'une heuristique, d'une zone grise ou d'une suggestion IA, et si une zone protégée doit être posée avant transformation.

---

## 9. Ce qu'il faut éviter

- implémentations globales sans tests ;
- fusion de plusieurs responsabilités ;
- modifications massives « pour harmoniser » ;
- appels à une IA sans encadrement ;
- normalisation silencieuse ;
- dépendance à des comportements implicites ;
- parsing fragile si un modèle plus robuste est possible ;
- transformation structurelle fondée sur un seul indice Word.

---

## 10. Règle d'or

Quand une décision oppose sophistication et clarté, automatisation et contrôle humain, puissance et traçabilité, IA et règle explicite, choisir clarté, contrôle humain, traçabilité et règle explicite si elle existe.

---

## 11. Gouvernance pipeline

Pour toute tâche touchant au pipeline éditorial, les documents prioritaires sont :

```text
docs/EDITORIAL_DECISION_MODEL.md
docs/EDITORIAL_PIPELINE.md
ARCHITECTURE.md
SPECS.md
```

Rappel : la sortie de production visée est l'XML-TEI Métopes ; le DOCX reste une sortie de relecture humaine ; l'IA reste optionnelle et encadrée.
