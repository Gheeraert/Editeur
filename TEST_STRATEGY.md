# Stratégie de test

## 1. Objet

Définir une stratégie de test compatible avec un développement modulaire, incrémental et assisté par Codex.

Le projet doit être testé non seulement comme une chaîne de correction, mais comme un système de décision éditoriale gouverné par un pivot Python‑JSON.

---

## 2. Principe général

Le projet doit avancer par couches :

1. tests unitaires sur logique isolée ;
2. tests du modèle pivot ;
3. tests de sérialisation / désérialisation JSON ;
4. tests sur fixtures ciblées ;
5. tests d'intégration entre modules ;
6. tests de non-régression ;
7. tests de prudence éditoriale ;
8. tests de cohérence entre exports.

Il ne faut pas dépendre d'un unique test de pipeline complet pour savoir si le projet tient.

---

## 3. Types de tests

### 3.1 Tests unitaires

Portent sur des fonctions ou classes précises : détection d'espace, normalisation de guillemets, diagnostic, rapport, sérialisation JSON, calcul de score, application d'un veto.

### 3.2 Tests du pivot

Portent sur le contrat Python‑JSON : types de blocs, champs requis, invariants, canonicalisation, cohérence des attributs.

Exemples :

- `quote_kind=poetry` implique `lineation=verse` ;
- un `heading` possède un `heading_level` valide ;
- un `table` ne perd pas son modèle tabulaire ;
- une zone protégée n'est pas confondue avec une structure canonique ;
- une sémantique reconstruite depuis des clés legacy n'est pas considérée comme canonique tant qu'elle n'est pas stockée dans le pivot.

### 3.3 Tests de sérialisation

Portent sur :

```text
Python Document -> JSON -> Python Document -> JSON
```

Le round‑trip doit être stable pour les champs documentés.

### 3.4 Tests sur fixtures

Portent sur un cas métier ciblé : `quotes_french_spacing`, `note_call_position`, `local_repetition_should_be_flagged`, `poetry_sequence_should_not_be_heading`, `code_block_should_be_protected`.

### 3.5 Tests d'intégration

Vérifient que deux ou trois modules coopèrent : ingestion + orthotypographie, ingestion + structure, structure + canonicalisation, pivot + export DOCX, pivot + export XML, XML + rendu HTML.

### 3.6 Tests de non-régression

Garantissent qu'un cas déjà résolu ne casse pas. Si un vers a été accidentellement promu en titre, créer une fixture minimale qui interdit cette régression.

### 3.7 Tests de prudence IA

Vérifient que l'IA s'abstient quand elle doit s'abstenir, ne réécrit pas massivement, ne modifie pas les citations, respecte les zones protégées et produit des suggestions locales.

### 3.8 Tests de cohérence entre exports

Vérifient que plusieurs sorties représentent le même pivot.

Exemple :

```text
pivot canonique : citation en vers
  -> DOCX : rendu comme vers
  -> XML : <lg>/<l>
  -> LaTeX : représentation versifiée
```

---

## 4. Politique de couverture

La couverture n'est pas une fin en soi. Priorité : stabilité des comportements critiques, lisibilité des tests, cas réels convertis en fixtures, absence de régression silencieuse, capacité d'abstention, cohérence du pivot.

---

## 5. Ce qui doit être testé en priorité

### Priorité absolue

- modèle de données minimal ;
- sérialisation JSON ;
- désérialisation JSON ;
- round‑trip JSON ;
- invariants du pivot ;
- distinction entre sémantique stockée et sémantique inférée ;
- règles orthotypographiques simples ;
- format des diagnostics ;
- structure des rapports ;
- non-confusion entre style Word et structure éditoriale.

### Priorité forte

- zones protégées ;
- reconnaissance de structures simples ;
- canonicalisation des décisions ;
- faux titres ;
- citations longues ;
- poésie ;
- listes accidentelles ;
- politique d'abstention du module IA ;
- lecture de XML de base ;
- rendu HTML minimal ;
- cohérence DOCX/XML/LaTeX.

---

## 6. Règles de qualité pour les tests

Un bon test doit être petit, explicite, stable, lié à un comportement précis, facile à relire et nommé d'après le problème qu'il protège.

Éviter les tests qui échouent pour dix raisons à la fois.

---

## 7. Organisation suggérée

```text
tests/
  unit/
    test_model.py
    test_serialization.py
    test_pivot_invariants.py
    test_pivot_canonicalization.py
    test_orthotypography_spacing.py
    test_structure_heading.py
    test_structure_poetry.py
    test_protected_zones.py
    test_reports.py
  integration/
    test_ingest_to_orthotypography.py
    test_ingest_to_structure.py
    test_structure_to_pivot.py
    test_pivot_to_docx.py
    test_pivot_to_tei_xml.py
    test_pivot_export_consistency.py
    test_xml_to_html.py
  fixtures/
    pivot_contract/
    structure_recognition/
    protected_zones/
    xml_methopes/
```

---

## 8. Gestion des cas ambigus

Certains cas ne produiront pas toujours une bonne réponse unique. Pour ces cas, préférer des assertions de type : présence ou absence de diagnostic, type de diagnostic, niveau de prudence, présence d'un veto, absence de transformation, interdiction de réécriture massive, interdiction de promotion en titre.

Exemple : un bloc ambigu peut rester paragraphe avec diagnostic ; il ne doit pas être automatiquement promu en titre.

---

## 9. Tests liés aux zones protégées

### Poésie

- une séquence de vers doit être reconnue ;
- un vers ne doit pas devenir un titre ;
- un vers accidentellement en liste doit être récupéré ou signalé ;
- un faux style Word `Titre` ne doit pas l'emporter sur une séquence poétique forte ;
- une zone protégée poésie doit être canonicalisée avant export ;
- une citation en vers doit produire des lignes exploitables dans le pivot.

### Code

- un bloc de code ne doit pas subir les corrections typographiques françaises ordinaires ;
- l'IA stylistique ne doit pas reformuler le code.

### Transcription linguistique

- les espaces, apostrophes, signes, alignements et notations ne doivent pas être normalisés sans règle dédiée.

### Tableau

- un tableau ne doit pas être aplati en paragraphes sans diagnostic.

---

## 10. Tests minimaux pour le problème poésie / XML

À ajouter avant toute correction de l'export XML :

```text
1. Un bloc canonique quote_block + quote_kind=poetry + lineation=verse
   produit en XML <cit><quote><lg><l>...

2. Un bloc quote_block avec protected_zone=poetry mais sans quote_kind
   échoue à la validation du pivot ou produit un diagnostic avant export.

3. Un bloc poétique avec InlineSpan(kind=line_break)
   est canonicalisé en lignes exploitables.

4. Un même pivot poétique donne un rendu cohérent DOCX/XML.

5. Une chronologie ou liste datée ne devient pas poésie.
```


## 10.1 Test minimal « stocké vs inféré »

Avant de considérer la passe pivot comme stabilisée, ajouter un test explicite :

```text
1. Construire un QuoteBlock legacy :
   attributes = {"quote_kind": "poetry", "protected_zone": "poetry"}
   sans attributes["semantic"].

2. Vérifier qu'avant canonicalization, ce bloc n'est pas un pivot canonique conforme.

3. Exécuter PivotCanonicalizer.

4. Vérifier que le JSON sérialisé contient :
   attributes.semantic.role = quote
   attributes.semantic.quote_kind = poetry
   attributes.semantic.lineation = verse
   attributes.semantic.lines = [...]

5. Vérifier qu'une transformation ou trace équivalente a été produite.

6. Vérifier que les exporteurs consomment cette sémantique stockée, et non les clés legacy.
```

Ce test protège le cœur du contrat : le pivot doit être explicite, non seulement reconstructible.

---

## 11. Non-régression éditoriale

Dès qu'un cas réel PURH important est stabilisé, il doit être converti en fixture courte, en test de non-régression et en note descriptive.

---

## 12. Dépendance aux sources réelles

Les documents réels servent à comprendre. Les tests doivent en extraire des cas courts. Ne pas faire reposer la stabilité du projet sur de gros fichiers opaques.

---

## 13. Déclenchement recommandé des tests

À chaque tâche Codex significative : lancer les tests unitaires concernés, les tests d'intégration directement touchés, les tests de non-régression associés, et mentionner les tests ajoutés ou adaptés.

Toute tâche touchant les exports doit aussi lancer les tests de validation du pivot.

---

## 14. Tests minimaux pour une passe structure

Toute passe touchant la reconnaissance structurelle devrait vérifier : vrai titre reconnu, paragraphe ordinaire non promu, citation longue reconnue ou diagnostiquée, séquence poétique protégée, faux heading Word neutralisé si conflit, liste réelle conservée, liste accidentelle en poésie non conservée comme puce, pivot canonicalisé avant export.
