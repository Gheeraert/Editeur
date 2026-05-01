# Regles Typographiques PURH (V1)

## 1. Objet

Ce document traduit les consignes PURH et les usages typographiques courants en regles de developpement prudentes.
Il ne vise pas l'exhaustivite de l'Imprimerie nationale.

## 2. Cadre de decision editorial

### Vetos structurels (prioritaires)

- Bloque une transformation meme si une heuristique donne un score eleve.
- Exemples: references de passage, legendes/pages, listes, bibliographie probable, code/balises.

Statut:
- Existant: oui
- Futur: extension fine des patterns

### Deterministe sur

- Auto-correction locale quand l'ambiguite est faible.
- Exemples: `etc...` -> `etc.`, normalisations d'espaces avec garde-fous, ordinaux simples.

Statut:
- Existant: oui (partiel selon regles)
- Futur: couverture testee plus large

### Heuristique scoree

- Utilisee quand la decision depend de plusieurs indices.
- Exemples: titraille, candidats citations poetiques.
- Doit produire: `score`, `decision`, `evidence`, `veto_reasons`, `ai_candidate`.

Statut:
- Existant: oui
- Futur: calibration continue sur corpus

### IA locale (zone grise)

- Usage cible: segments `ai_candidate` uniquement.
- Reponse structuree attendue.
- Les vetos restent non contournables (etat actuel).

Statut:
- Existant: cadre prudent
- Futur: activation locale explicite

### IA exploratoire future

- Desactivee par defaut.
- Suggestions uniquement, pas corrections silencieuses.

Statut:
- Existant: non
- Futur: oui

## 3. Familles de regles prioritaires

### Espaces / ponctuation

- `R-SP-001` espace avant `: ; ?!` en phrase simple + garde-fous
- `R-SP-002` suppression espace avant `, .`
- `R-SP-003` doubles espaces
- `R-SP-004` milliers

### Abreviations / ordinaux

- `R-AB-001` `etc.` propre
- `R-AB-003` abreviations bibliographiques courantes (notes)
- `R-SO-002` ordinaux simples

### Notes / guillemets / citations

- `R-AN-002`, `R-AN-003` en diagnostic prudent
- `R-GQ-004` en diagnostic prudent
- distinctions de citations complexes: priorite au diagnostic

## 4. Principes de prudence

- correction locale avant tout
- pas de reecriture massive
- en cas de doute: diagnostic
- IA sous controle humain

## 5. Points explicitement futurs

- IA locale active sur toutes les zones grises (non generalise)
- IA exploratoire parametree
- normalisation bibliographique exhaustive
