# Pipeline éditorial PURH

## 1. Finalité

Le projet prépare des manuscrits auteur pour la production PURH.

Le pivot est le modèle Python‑JSON :

```text
Document Python canonicalisé <=> JSON pivot versionné
```

Les sorties DOCX, XML‑TEI, LaTeX, HTML et PDF sont des représentations de ce pivot.

---

## 2. Pipeline cible

```text
DOCX auteur
  -> import riche
  -> extraction des faits documentaires
  -> modèle Python initial
  -> décisions / corrections / structuration éditoriale
  -> canonicalisation du pivot
  -> validation des invariants
  -> JSON pivot
  -> sorties :
       1) DOCX de relecture humaine
       2) XML‑TEI Métopes de production
       3) LaTeX / HTML / PDF selon besoins
```

---

## 3. Règle centrale

```text
L'amont décide ; le pivot enregistre ; l'aval représente.
```

Les exporteurs ne doivent pas compenser un pivot incomplet.

---

## 4. Étapes du pipeline

### 4.1 Import riche

Rôle : importer le document source et conserver les faits matériels.

Exemples :

- texte ;
- inlines ;
- notes ;
- styles Word ;
- sauts de ligne ;
- sauts de page ;
- tableaux ;
- listes ;
- retraits ;
- informations de paragraphe.

Sortie : `Document` initial, non nécessairement canonicalisé.

### 4.2 Extraction des faits documentaires

Rôle : organiser les faits source sans les transformer en structures éditoriales trop vite.

Exemple :

```text
style Word = Titre 2
```

est un fait source, non une décision.

### 4.3 Identification des zones protégées

Rôle : repérer tôt les zones qui doivent empêcher des transformations concurrentes.

Exemples : poésie, citation ancienne, tableau, code, transcription linguistique, bibliographie.

Une zone protégée pose un veto ou un régime de prudence. Elle ne suffit pas toujours à définir la structure finale.

### 4.4 Contrôle orthotypographique

Rôle : appliquer ou proposer des corrections locales explicites, avec garde‑fous.

Ce module doit respecter les zones protégées.

### 4.5 Reconnaissance structurelle

Rôle : produire des candidats, scores, vetos, diagnostics et transformations structurelles.

Exemples :

- titre ;
- citation ;
- citation en vers ;
- bibliographie ;
- liste ;
- tableau ;
- code.

### 4.6 IA locale encadrée

Rôle : arbitrer certains cas gris sur question fermée, si la configuration l'autorise.

L'IA ne réécrit pas et ne remplace pas les vetos.

### 4.7 Canonicalisation du pivot

Rôle : inscrire les décisions retenues dans une représentation stable.

Exemple pour la poésie :

```text
séquence reconnue comme versifiée
  -> block_type = quote_block
  -> quote_kind = poetry
  -> lineation = verse
  -> protected_zone = poetry
  -> lignes exploitables
```

La canonicalisation est une étape obligatoire avant tout export de production.

### 4.8 Validation des invariants

Rôle : vérifier que le pivot est cohérent.

Exemples :

```text
heading => heading_level présent
quote_kind=poetry => lineation=verse
lineation=verse => lignes exploitables
table => structure conservée ou fallback diagnostiqué
```

Un pivot incohérent doit produire un diagnostic avant export.

### 4.9 JSON pivot

Rôle : écrire une représentation sérialisée, versionnée, relisible et testable du pivot.

Ce JSON sert aux fixtures, aux comparaisons, au debug et à la revue humaine technique.

### 4.10 Exports

Rôle : représenter le pivot.

- DOCX : relecture humaine ;
- XML‑TEI Métopes : production ;
- LaTeX : typographie ou impression ;
- HTML/PDF : visualisation et contrôle.

---

## 5. Niveaux de décision éditoriale

### 5.0 Modes de décision

Le pipeline prépare quatre modes de décision :

- `deterministic`
- `heuristic`
- `heuristic_ai_local`
- `ai_exploratory` réservé

Comportement attendu :

- `deterministic` : aucun appel IA ; seules les règles sûres s'appliquent ;
- `heuristic` : heuristiques scorées + diagnostics ; aucun appel IA ;
- `heuristic_ai_local` : heuristiques scorées + arbitrage IA structurel local sur zones grises uniquement ;
- `ai_exploratory` : analyse non automatique, désactivée par défaut.

### 5.1 Vetos structurels

Rôle : bloquer une transformation même si un score est élevé.

Exemples :

- référence de passage (`VI, I, 52`, `VIII, Pr., 18`) ;
- légende/reference (`page 305`, `p. 390`, `accolade`, `face à`, `souligné`) ;
- liste réelle ;
- bibliographie probable ;
- code/balise technique ;
- poésie probable ;
- tableau.

Les vetos restent prioritaires quel que soit le profil.

### 5.2 Déterministe sûr

Rôle : transformation locale automatique quand la règle est sûre.

Exemples :

- `etc...` -> `etc.` ;
- ordinaux simples ;
- espaces typographiques avec garde‑fous ;
- siècles stylés quand le contexte est robuste.

### 5.3 Heuristique scorée

Rôle : arbitrer quand plusieurs indices sont nécessaires.

Sortie attendue :

- `score` ;
- `decision` (`transform` / `diagnostic` / `ignore`) ;
- `evidence` ;
- `veto_reasons` ;
- `ai_candidate`.

### 5.4 IA locale

Rôle : assistance sur zones grises uniquement, jamais sur tout le document.

Contraintes :

- réponse structurée ;
- pas d'override des vetos ;
- pas de correction silencieuse globale ;
- appel limité aux candidats heuristiques `ai_candidate=true` ;
- aucun appel si `veto_reasons` non vide ;
- aucun appel si `enable_structure_ai=false` ;
- arbitrage de classification locale uniquement.

### 5.5 IA exploratoire future

Rôle : suggestions plus ouvertes, contrôlées, désactivées par défaut.

Contraintes : suggestions uniquement, jamais corrections silencieuses.

---

## 6. Rôles des sorties

- JSON : contrat sérialisé du pivot, utile pour debug/tests/traçabilité.
- DOCX : sortie de relecture humaine.
- XML‑TEI Métopes : sortie de production principale.
- LaTeX : projection typographique à rattacher au pivot.
- HTML/PDF : visualisation et contrôle.

---

## 7. Point d'attention Métopes

Les styles Word Métopes ne remplacent pas la structure TEI Métopes.

Le mapping évolue d'une logique « style Word » vers une logique « rôle éditorial structurable ».

```text
style Word -> indice ou rendu
pivot -> structure
XML‑TEI -> projection de production
```

---

## 8. Exemple critique : poésie

Mauvais pipeline :

```text
Word détecte visuellement les vers
DOCX les rend à peu près correctement
XML redétecte partiellement
LaTeX redétecte autrement
```

Bon pipeline :

```text
structure_service reconnaît ou diagnostique la poésie
canonicalizer inscrit quote_kind=poetry + lineation=verse
validator vérifie les lignes
DOCX, XML et LaTeX représentent cette décision
```

---

## 9. Principes de prudence

- correction locale et motivée ;
- pas de réécriture massive ;
- en cas de doute : diagnostic plutôt qu'automatisation ;
- IA d'assistance sous contrôle humain ;
- pas de patch de sortie pour compenser un pivot fragile ;
- tests d'invariants avant tests de rendu.
