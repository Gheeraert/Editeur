# EDITORIAL_DECISION_MODEL.md

## 1. Objet

Ce document décrit le modèle de décision éditoriale du projet PURH Editorial Studio.

Il répond à une difficulté centrale : un manuscrit auteur, notamment sous forme DOCX, ne contient pas directement des structures éditoriales fiables. Il contient des faits matériels : styles Word, gras, italique, petites capitales, retraits, puces, notes, tableaux, légendes, code, poésie, transcriptions spécialisées, accidents de mise en forme.

Ces faits doivent être interprétés, pondérés, puis éventuellement transformés.

Le but du modèle est de rendre cette interprétation explicite, testable, traçable, prudente et compatible avec une validation humaine.

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
  -> transformation éventuelle
```

---

## 3. Faits documentaires

Les faits documentaires sont les informations observées dans le fichier source : `style_name`, `style_id`, `all_runs_bold`, `all_runs_italic`, `ind_left`, `ind_first_line`, `num_id`, `numbering_level`, `is_list`, `text`, `inlines`, `note_refs`.

Ils doivent être conservés autant que possible. Ils ne doivent pas être confondus avec une décision éditoriale.

---

## 4. Indices et candidats

Les indices sont des faits interprétés : bloc court, majuscule initiale, absence de ponctuation finale, style Word de titre, longueur homogène avec les blocs voisins, ponctuation finale régulière, retrait gauche important, numérotation Word.

Un même bloc peut recevoir plusieurs candidats concurrents.

Exemple : `Le Ciel brille d'éclairs, s'entr'ouvre, et parmi nous` peut ressembler à un titre, une liste, un vers ou un paragraphe ordinaire.

Le système doit pouvoir représenter ce conflit.

---

## 5. Vetos

Un veto interdit une transformation, même si un score partiel est élevé.

Exemples : une référence bibliographique ne doit pas devenir un titre ; un passage de code ne doit pas subir la typographie française ordinaire ; une séquence poétique ne doit pas laisser un vers isolé devenir heading ; une transcription linguistique ne doit pas être normalisée comme prose ordinaire.

Les vetos sont prioritaires.

---

## 6. Zones protégées

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

---

## 7. Régimes d'action

### 7.1 Déterministe

Le déterministe s'applique lorsque la règle est explicite, locale et sûre : correction d'une espace validée, transformation d'un style Métopes explicite, normalisation d'un siècle selon règle documentée.

Sortie attendue : transformation locale, `rule_id`, trace dans `Transformation`.

### 7.2 Heuristique scorée

L'heuristique scorée s'applique lorsque la structure est probable mais doit être évaluée.

Chaque décision doit produire : `score`, `decision`, `evidence`, `veto_reasons`, `ai_candidate`.

Décisions possibles : `ignore`, `diagnostic`, `transform`.

Interprétation : score faible = pas touche ; score moyen = diagnostic / zone grise ; score élevé = transformation si aucun veto.

### 7.3 IA locale encadrée

L'IA locale intervient uniquement dans une zone grise. Elle reçoit une question bornée, ne réécrit pas, ne transforme pas directement, ne passe pas outre les vetos et peut s'abstenir.

### 7.4 IA exploratoire ou freestyle

L'IA exploratoire est désactivée par défaut. Elle peut servir à comprendre un cas documentaire rare ou à produire une hypothèse. Elle ne doit jamais modifier automatiquement le texte source.

Elle constitue une solution de dernier recours.

---

## 8. Ordre recommandé des décisions

1. importer les faits ;
2. repérer les zones protégées ;
3. poser les vetos ;
4. calculer les candidats ;
5. arbitrer les conflits ;
6. appliquer les transformations sûres ;
7. produire des diagnostics pour les zones grises ;
8. recourir éventuellement à l'IA locale ;
9. réserver l'IA exploratoire à l'analyse non automatique.

Ne jamais commencer par promouvoir les titres avant d'avoir cherché les zones protégées.

---

## 9. Exemple : poésie contre faux titre

Mauvaise décision :

```text
bloc court + majuscule + style titre
  -> heading
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
  -> sinon diagnostic
```

La poésie se reconnaît par séquence ; le titre se reconnaît souvent bloc par bloc. La séquence doit donc passer avant le bloc isolé.

---

## 10. Exemple : code contre orthotypographie

Un bloc contenant `print("Hello: world")` ne doit pas recevoir automatiquement la typographie française des deux-points.

Bonne décision : candidat code -> `protected_zone = code` -> corrections typographiques ordinaires désactivées -> diagnostic seulement si nécessaire.

---

## 11. Exemple : transcription linguistique

Une transcription peut contenir des signes, espaces, barres, crochets, apostrophes ou alignements spécialisés. Elle ne doit pas être normalisée comme un paragraphe ordinaire.

Bonne décision : candidat transcription linguistique -> `protected_zone = linguistic_transcription` -> corrections ordinaires désactivées -> validation humaine si ambigu.

---

## 12. Exigences pour les diagnostics

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

## 13. Exigences pour les transformations

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
    "score": 0.91
  }
}
```

---

## 14. Ce que l'IA ne doit pas faire

L'IA ne doit pas décider seule d'une structure, réécrire automatiquement, corriger une citation, normaliser un code, lisser une prose savante, passer outre un veto, remplacer les tests ou remplacer une règle déterministe.

---

## 15. Critères de réussite

Le modèle est satisfaisant s'il évite les faux positifs destructeurs, explique ses décisions, sait ne pas décider, distingue les faits et les interprétations, protège les zones sensibles, reste testable par fixtures et permet d'aller vers XML-TEI Métopes sans confondre style Word et structure TEI.

---

## 16. Formule de synthèse

Le texte n'est pas seulement une suite de caractères. Dans ce projet, un texte est une suite d'unités documentaires interprétées sous contrainte matérielle, éditoriale, typographique, structurelle et humaine.

Une théorie éditoriale utile doit pouvoir s'encoder. Si elle ne peut produire ni diagnostic, ni veto, ni transformation vérifiable, elle reste insuffisamment opératoire.
