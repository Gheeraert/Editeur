# AGENTS.md

## 1. Rôle de ce fichier

Ce document fixe les règles de travail pour l'assistant de développement utilisé sur ce projet, notamment Codex AI.

Le projet est un correcteur ortho-typographique assisté pour les PURH (Presses universitaires de Rouen et du Havre) : ouvrir une copie d'un manuscrit Word, appliquer les règles du catalogue, surligner chaque intervention, enregistrer un nouveau DOCX. Le développement doit rester strictement encadré, modulaire, testable, traçable et prudent sur le plan éditorial.

L'architecture antérieure (pivot Python‑JSON, moteur de score/seuil, IA multi-niveaux, exports multiples) a été abandonnée après plusieurs refontes infructueuses et intégralement supprimée du dépôt. Elle reste consultable à titre d'archive dans `docs/legacy/` si une future tâche a besoin d'y retrouver des expressions régulières, des listes lexicales ou des cas de test.

---

## 2. Principes impératifs

### 2.1 Pas de monolithe

Ne jamais concentrer des responsabilités hétérogènes dans un gros script unique. `corrector/word_document.py` pilote Word, `corrector/runner.py` orchestre les règles dans un ordre explicite, `corrector/rules/*.py` contient les règles par famille — cette séparation ne doit pas se dissoudre au fil des ajouts.

### 2.2 Développement incrémental

Toute demande ordinaire doit être traitée par petits périmètres : une règle, une famille de tests, un garde-fou ciblé. Pas de refactorisation massive « pour harmoniser » hors demande explicite.

### 2.3 Tests obligatoires

Toute évolution significative doit s'accompagner de tests : cas positifs, cas négatifs (garde-fous), idempotence (un second passage ne doit pas répéter la même correction). `python -m pytest` doit rester vert.

### 2.4 Aucune invention normative silencieuse

Ne pas inventer de règles PURH ni de style Word cible non spécifié par le catalogue. Lorsqu'une norme locale n'est pas documentée ou que l'action concrète à appliquer n'est pas claire : préférer un diagnostic (surlignage turquoise, texte inchangé) à une transformation automatique devinée.

### 2.5 Aucun score, aucun seuil

Le chemin d'exécution actuel (« reborn », voir `docs/REBORN_ARCHITECTURE.md`) n'utilise ni score de confiance, ni seuil, ni profil de prudence, ni moteur de décision générique. Une règle est une petite fonction (ou une donnée simple associée à une fonction), avec un déclencheur explicite et testable — jamais une pondération d'indices.

### 2.6 Préserver la traçabilité

Chaque intervention automatique doit être surlignée dans le DOCX de sortie (jaune = transformation, turquoise = diagnostic) et rattachée à un `rule_id` stable du catalogue. Une transformation sans surlignage est un bug.

### 2.7 Préférer la lisibilité à l'astuce

Le code attendu doit être clair, typé si possible, modulaire, sans magie inutile. Les garde-fous et exceptions d'une règle sont écrits à proximité immédiate de cette règle, pas déplacés dans un moteur général d'exceptions.

### 2.8 Refuser les dépendances lourdes sans justification

Ne pas ajouter de dépendance sans raison claire. Le seul prérequis technique actuel est `pywin32` (automatisation Word).

---

## 3. Le catalogue des 61 règles

`docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md` est la source de vérité éditoriale du projet : périmètre, identifiants stables, nature (`deterministic`/`heuristic`), type d'action. Il ne doit pas être modifié sans très bonne raison, et jamais pour faire correspondre le catalogue à une implémentation partielle — c'est l'inverse qui doit être vrai (cf. `docs/REBORN_ARCHITECTURE.md` §2.1 pour l'état réel de couverture).

Un `rule_id` doit être un identifiant explicite et lisible par un humain (`purh.famille.detail`), jamais un code opaque de la forme `R-XX-000`.

---

## 4. Méthode de livraison attendue

Pour toute tâche de développement, préciser : fichiers modifiés/créés, règle(s) concernée(s) et leur `rule_id`, garde-fous ajoutés, tests ajoutés et exécutés, ce qui reste volontairement hors périmètre (et pourquoi — cf. §2.4).

---

## 5. Ce qu'il faut éviter

- implémentations sans tests ;
- règle qui compte un `rule_id` sans détecteur réellement câblé (un compte à 0 doit signifier « rien à corriger », jamais « règle non implémentée ») ;
- réintroduction d'un score, d'un seuil ou d'un profil de prudence ;
- transformation silencieuse (sans surlignage) ;
- devinette d'un style Word cible ou d'une norme PURH non documentée.

---

## 6. Règle d'or

Entre sophistication et clarté, automatisation et contrôle humain, choisir clarté et contrôle humain. Une intervention douteuse doit être signalée (diagnostic), pas appliquée par optimisme.
