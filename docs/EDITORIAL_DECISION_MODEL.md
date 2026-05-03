# Modèle de décision éditoriale

## 1. Objet

Ce document décrit le modèle de décision éditoriale du projet PURH Editorial Studio.

Il répond à une difficulté centrale : un manuscrit auteur, notamment sous forme DOCX, ne contient pas directement des structures éditoriales fiables. Il contient des faits matériels : styles Word, gras, italique, petites capitales, retraits, puces, notes, tableaux, légendes, code, poésie, transcriptions spécialisées, accidents de mise en forme.

Ces faits doivent être interprétés, pondérés, puis éventuellement transformés.

Le but du modèle est de rendre cette interprétation explicite, testable, traçable, prudente, compatible avec une validation humaine et inscrite dans un pivot Python‑JSON stable.

---

## 2. Principe fondamental

Un fait Word n'est pas une structure éditoriale.

```text
style Word ≠ structure éditoriale
style Word ≠ structure TEI
mise en forme ≠ intention
```

Un style `Titre 2` peut signaler un titre, mais aussi une erreur. Une puce peut signaler une liste, mais aussi un accident. Un paragraphe court peut être un intertitre, mais aussi un vers.

Le système doit donc distinguer :

```text
faits documentaires
  -> indices
  -> candidats
  -> conflits
  -> vetos
  -> décision
  -> canonicalisation
  -> validation du pivot
  -> export
```

---

## 3. Deuxième principe : les sorties ne décident pas

Les sorties DOCX, XML‑TEI, LaTeX, HTML ou PDF ne doivent pas être des lieux de décision structurelle.

Elles doivent représenter un pivot déjà décidé et validé.

```text
l'amont décide ; le pivot enregistre ; l'aval représente
```

Si une sortie doit deviner qu'un bloc est un titre, un vers ou une liste, c'est que le pivot est incomplet.

---

## 4. Faits documentaires

Les faits documentaires sont les informations observées dans le fichier source : `style_name`, `style_id`, `all_runs_bold`, `all_runs_italic`, `ind_left`, `ind_first_line`, `num_id`, `numbering_level`, `is_list`, `text`, `inlines`, `note_refs`, `line_breaks`, `table_ooxml`.

Ils doivent être conservés autant que possible. Ils ne doivent pas être confondus avec une décision éditoriale.

---

## 5. Indices et candidats

Les indices sont des faits interprétés : bloc court, majuscule initiale, absence de ponctuation finale, style Word de titre, longueur homogène avec les blocs voisins, ponctuation finale régulière, retrait gauche important, numérotation Word.

Un même bloc peut recevoir plusieurs candidats concurrents.

Exemple : `Le Ciel brille d'éclairs, s'entr'ouvre, et parmi nous` peut ressembler à un titre, une liste, un vers ou un paragraphe ordinaire.

Le système doit pouvoir représenter ce conflit.

---

## 6. Vetos

Un veto interdit une transformation, même si un score partiel est élevé.

Exemples : une référence bibliographique ne doit pas devenir un titre ; un passage de code ne doit pas subir la typographie française ordinaire ; une séquence poétique ne doit pas laisser un vers isolé devenir heading ; une transcription linguistique ne doit pas être normalisée comme prose ordinaire.

Les vetos sont prioritaires.

---

## 7. Zones protégées

Une zone protégée est un bloc ou une séquence qui réclame des règles particulières.

Types initiaux : `poetry`, `quote`, `old_quote`, `code`, `linguistic_transcription`, `table`, `formula`, `bibliography`, `caption`.

Une zone protégée peut bloquer : promotion en titre, transformation en liste, correction orthotypographique, suggestion stylistique, normalisation d'espaces, réécriture IA.

Représentation minimale possible :

```json
{
  "protected_zone": "poetry",
  "protected_zone_score": 0.91,
  "protected_zone_rule": "structure.poetry.sequence"
}
```

Attention : une zone protégée est un mécanisme de prudence ou de veto. Elle ne suffit pas toujours à définir la structure finale.

Exemple : `protected_zone=poetry` doit empêcher une promotion en titre, mais il faut encore canonicaliser le bloc en citation en vers pour produire un XML `<lg>/<l>`.

---

## 8. Décision et canonicalisation

Une décision éditoriale devient réellement exploitable lorsqu'elle est inscrite dans le pivot.

Exemple transitoire pour une citation en vers :

```json
{
  "block_type": "quote_block",
  "attributes": {
    "semantic_role": "quote",
    "quote_kind": "poetry",
    "lineation": "verse",
    "protected_zone": "poetry"
  }
}
```

Cette étape est la canonicalisation.

Elle permet aux sorties de ne plus redétecter la structure.

---

## 9. Régimes d'action

### 9.1 Déterministe

Le déterministe s'applique lorsque la règle est explicite, locale et sûre : correction d'une espace validée, transformation d'un style Métopes explicite déjà canonicalisé, normalisation d'un siècle selon règle documentée.

Sortie attendue : transformation locale, `rule_id`, trace dans `Transformation`.

### 9.2 Heuristique scorée

L'heuristique scorée s'applique lorsque la structure est probable mais doit être évaluée.

Chaque décision doit produire : `score`, `decision`, `evidence`, `veto_reasons`, `ai_candidate`.

Décisions possibles : `ignore`, `diagnostic`, `transform`.

Interprétation : score faible = pas touche ; score moyen = diagnostic / zone grise ; score élevé = transformation si aucun veto.

### 9.3 IA locale encadrée

L'IA locale intervient uniquement dans une zone grise. Elle reçoit une question bornée, ne réécrit pas, ne transforme pas directement, ne passe pas outre les vetos et peut s'abstenir.

### 9.4 IA exploratoire ou freestyle

L'IA exploratoire est désactivée par défaut. Elle peut servir à comprendre un cas documentaire rare ou à produire une hypothèse. Elle ne doit jamais modifier automatiquement le texte source.

Elle constitue une solution de dernier recours.

---

## 10. Ordre recommandé des décisions

1. importer les faits ;
2. repérer les zones protégées ;
3. poser les vetos ;
4. calculer les candidats ;
5. arbitrer les conflits ;
6. appliquer les transformations sûres ;
7. produire des diagnostics pour les zones grises ;
8. recourir éventuellement à l'IA locale ;
9. canonicaliser les décisions retenues ;
10. valider les invariants du pivot ;
11. exporter.

Ne jamais commencer par promouvoir les titres avant d'avoir cherché les zones protégées.

Ne jamais exporter en production sans pivot validé.

---

## 11. Exemple : poésie contre faux titre

Mauvaise décision :

```text
bloc court + majuscule + style titre
  -> heading
```

Mauvaise réparation :

```text
l'export XML reconnaît après coup que c'était peut-être un vers
  -> produit localement <l>
```

Bonne décision :

```text
séquence de plusieurs lignes courtes
+ ponctuation de vers
+ homogénéité
+ contexte poétique
  -> protected_zone = poetry
  -> bloquer heading
  -> transformer en quote_block poetry si score élevé
  -> canonicaliser quote_kind=poetry + lineation=verse
  -> sinon diagnostic
```

La poésie se reconnaît par séquence ; le titre se reconnaît souvent bloc par bloc. La séquence doit donc passer avant le bloc isolé.

---

## 12. Exemple : code contre orthotypographie

Un bloc contenant `print("Hello: world")` ne doit pas recevoir automatiquement la typographie française des deux-points.

Bonne décision : candidat code -> `protected_zone = code` -> corrections typographiques ordinaires désactivées -> diagnostic seulement si nécessaire.

---

## 13. Exemple : transcription linguistique

Une transcription peut contenir des signes, espaces, barres, crochets, apostrophes ou alignements spécialisés. Elle ne doit pas être normalisée comme un paragraphe ordinaire.

Bonne décision : candidat transcription linguistique -> `protected_zone = linguistic_transcription` -> corrections ordinaires désactivées -> validation humaine si ambigu.

---

## 14. Exigences pour les diagnostics

Tout diagnostic structurel devrait contenir : bloc ou séquence cible, catégorie, score éventuel, indices, vetos, décision, transformation proposée ou refusée, statut de validation.

Exemple :

```json
{
  "category": "heading_candidate",
  "score": 0.62,
  "decision": "diagnostic",
  "veto_reasons": ["poetry_sequence_candidate"],
  "evidence": {
    "text": "Et j'ai vu d'un œil satisfait.",
    "poetry_score": 0.91
  }
}
```

---

## 15. Exigences pour les transformations

Toute transformation doit être localisée, justifiée, réversible, testable et tracée.

Exemple :

```json
{
  "operation": "annotate_structure",
  "before": "paragraph",
  "after": "quote_block",
  "rule_id": "structure.poetry.quote",
  "attributes": {
    "quote_kind": "poetry",
    "lineation": "verse",
    "score": 0.91
  }
}
```

---

## 16. Exigences pour les invariants du pivot

Après canonicalisation, certains invariants doivent être vérifiés.

Exemples :

```text
quote_kind == poetry => lineation == verse
lineation == verse => lignes exploitables
block_type == heading => heading_level présent
block_type == table => structure conservée ou fallback diagnostiqué
```

Un invariant violé doit produire un diagnostic avant export.

---

## 17. Ce que l'IA ne doit pas faire

L'IA ne doit pas décider seule d'une structure, réécrire automatiquement, corriger une citation, normaliser un code, lisser une prose savante, passer outre un veto, remplacer les tests ou remplacer une règle déterministe.

Elle ne doit pas non plus compenser un contrat de pivot mal défini.

---

## 18. Critères de réussite

Le modèle est satisfaisant s'il évite les faux positifs destructeurs, explique ses décisions, sait ne pas décider, distingue les faits et les interprétations, protège les zones sensibles, reste testable par fixtures et permet d'aller vers XML‑TEI Métopes sans confondre style Word, rendu DOCX et structure TEI.

---

## 19. Formule de synthèse

Le texte n'est pas seulement une suite de caractères. Dans ce projet, un texte est une suite d'unités documentaires interprétées sous contrainte matérielle, éditoriale, typographique, structurelle et humaine.

Une théorie éditoriale utile doit pouvoir s'encoder. Si elle ne peut produire ni diagnostic, ni veto, ni transformation vérifiable, ni invariant de pivot, elle reste insuffisamment opératoire.
