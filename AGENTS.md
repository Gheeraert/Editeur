# AGENTS.md

## Rôle de ce fichier

Ce document fixe les règles de travail pour l'assistant de développement utilisé sur ce projet, notamment Codex AI.

Le projet concerne une chaîne modulaire de préparation éditoriale pour les PURH.
Le développement doit rester strictement encadré, modulaire et testable.

---

## Principes impératifs

### 1. Pas de monolithe
Ne jamais concentrer des responsabilités hétérogènes dans un gros script unique.

Séparer clairement :
- modèle de données ;
- logique métier ;
- lecture / écriture de fichiers ;
- sérialisation JSON ;
- appels éventuels à des API IA ;
- rendu / visualisation ;
- CLI ou interface éventuelle.

### 2. Développement incrémental
Toute demande doit être traitée par petits périmètres :
- une fonction ;
- un module ;
- un mapping ;
- une famille de tests ;
- une règle éditoriale isolée.

Éviter les refontes globales tant qu'un comportement local n'est pas stabilisé.

### 3. Tests obligatoires
Toute évolution significative doit s'accompagner de tests.

Au minimum :
- tests unitaires sur la logique ;
- fixtures minimales ;
- absence de régression sur les cas déjà stabilisés.

### 4. Aucune invention normative silencieuse
Ne pas inventer de règles PURH.
Lorsqu'une norme locale n'est pas documentée :
- expliciter l'hypothèse ;
- isoler la règle ;
- la marquer comme provisoire ;
- préférer un comportement conservateur.

### 5. Prudence maximale pour l'IA stylistique
Le module IA ne doit jamais :
- réécrire massivement un texte ;
- uniformiser abusivement un style savant ;
- modifier silencieusement le texte source ;
- confondre préférence stylistique et faute.

Les suggestions doivent rester :
- locales ;
- motivées ;
- révisables ;
- optionnelles.

### 6. Préserver la traçabilité
Toute transformation doit pouvoir être :
- identifiée ;
- journalisée ;
- expliquée ;
- annulée.

### 7. Préférer la lisibilité à l'astuce
Le code attendu doit être :
- clair ;
- typé si possible ;
- modulaire ;
- documenté ;
- sans "magie" inutile.

### 8. Refuser les dépendances lourdes sans justification
Ne pas ajouter de dépendance importante sans raison claire.
Privilégier la standard library et quelques bibliothèques stables si nécessaire.

---

## Représentation des données

Le cœur du projet doit utiliser des **dataclasses Python**.
Le JSON sert à :
- sérialiser les états ;
- fabriquer les fixtures ;
- échanger entre modules si nécessaire ;
- déboguer.

Ne pas bâtir le cœur métier sur des dictionnaires non typés si une dataclass claire est préférable.

---

## Méthode de livraison attendue

Pour toute tâche de développement, fournir :
1. les fichiers modifiés / créés ;
2. les choix d'architecture ;
3. les limites connues ;
4. les tests ajoutés ;
5. ce qui reste volontairement hors périmètre.

---

## Ce qu'il faut faire avant de coder

Toujours vérifier :
- quel document de cadrage gouverne la tâche ;
- quelles fixtures existent déjà ;
- quel comportement attendu est vérifiable ;
- si le cas demandé relève d'une règle déterministe ou d'une suggestion IA.

---

## Ce qu'il faut éviter

- implémentations globales sans tests ;
- fusion de plusieurs responsabilités ;
- modifications massives "pour harmoniser" ;
- appels à une IA sans encadrement de sortie ;
- normalisation silencieuse des textes ;
- dépendance à des comportements implicites ;
- parsing fragile si un modèle plus robuste est possible.

---

## Style de code recommandé

- modules courts ;
- fonctions cohérentes ;
- noms explicites ;
- dataclasses pour les objets métier ;
- structures de retour claires ;
- exceptions métier ciblées ;
- diagnostics structurés.

---

## Interaction avec les fixtures

Les fixtures ne sont pas des archives "réalistes" au sens documentaire.
Elles doivent être :
- petites ;
- ciblées ;
- nommées explicitement ;
- reliées à un comportement testable.

Un document réel volumineux doit d'abord servir de **source**, puis être découpé en **fixtures minimales**.

---

## Règle d'or

Quand une décision oppose :
- sophistication vs clarté,
- automatisation vs contrôle humain,
- puissance vs traçabilité,

toujours choisir :
- clarté,
- contrôle humain,
- traçabilité.

---

## Gouvernance pipeline

Pour toute t�che touchant au pipeline �ditorial, le document de cadrage prioritaire est docs/EDITORIAL_PIPELINE.md.

Rappel de cible :
- la sortie de production vis�e est l'XML-TEI M�topes ;
- le DOCX reste une sortie de relecture humaine.

