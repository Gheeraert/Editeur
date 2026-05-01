# TEST_STRATEGY.md

## 1. Objet

Définir une stratégie de test compatible avec un développement modulaire, incrémental et assisté par Codex.

Le projet doit être testé non seulement comme une chaîne de correction, mais comme un système de décision éditoriale.

---

## 2. Principe général

Le projet doit avancer par couches :

1. tests unitaires sur logique isolée ;
2. tests sur fixtures ciblées ;
3. tests d'intégration entre modules ;
4. tests de non-régression ;
5. tests de prudence éditoriale.

Il ne faut pas dépendre d'un unique test de pipeline complet pour savoir si le projet tient.

---

## 3. Types de tests

### 3.1 Tests unitaires

Portent sur des fonctions ou classes précises : détection d'espace, normalisation de guillemets, diagnostic, rapport, sérialisation JSON, calcul de score, application d'un veto.

### 3.2 Tests sur fixtures

Portent sur un cas métier ciblé : `quotes_french_spacing`, `note_call_position`, `local_repetition_should_be_flagged`, `poetry_sequence_should_not_be_heading`, `code_block_should_be_protected`.

### 3.3 Tests d'intégration

Vérifient que deux ou trois modules coopèrent : ingestion + orthotypographie, ingestion + structure, structure + export DOCX, XML + rendu HTML, zone protégée + désactivation des corrections ordinaires.

### 3.4 Tests de non-régression

Garantissent qu'un cas déjà résolu ne casse pas. Si un vers a été accidentellement promu en titre, créer une fixture minimale qui interdit cette régression.

### 3.5 Tests de prudence IA

Vérifient que l'IA s'abstient quand elle doit s'abstenir, ne réécrit pas massivement, ne modifie pas les citations, respecte les zones protégées et produit des suggestions locales.

---

## 4. Politique de couverture

La couverture n'est pas une fin en soi. Priorité : stabilité des comportements critiques, lisibilité des tests, cas réels convertis en fixtures, absence de régression silencieuse, capacité d'abstention.

---

## 5. Ce qui doit être testé en priorité

### Priorité absolue

- modèle de données minimal ;
- sérialisation JSON ;
- règles orthotypographiques simples ;
- format des diagnostics ;
- structure des rapports ;
- non-confusion entre style Word et structure éditoriale.

### Priorité forte

- zones protégées ;
- reconnaissance de structures simples ;
- faux titres ;
- citations longues ;
- poésie ;
- listes accidentelles ;
- politique d'abstention du module IA ;
- lecture de XML de base ;
- rendu HTML minimal.

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
    test_orthotypography_spacing.py
    test_structure_heading.py
    test_structure_poetry.py
    test_protected_zones.py
    test_reports.py
  integration/
    test_ingest_to_orthotypography.py
    test_ingest_to_structure.py
    test_structure_to_docx.py
    test_xml_to_html.py
  fixtures/
    ...
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
- un faux style Word `Titre` ne doit pas l'emporter sur une séquence poétique forte.

### Code

- un bloc de code ne doit pas subir les corrections typographiques françaises ordinaires ;
- l'IA stylistique ne doit pas reformuler le code.

### Transcription linguistique

- les espaces, apostrophes, signes, alignements et notations ne doivent pas être normalisés sans règle dédiée.

### Tableau

- un tableau ne doit pas être aplati en paragraphes sans diagnostic.

---

## 10. Non-régression éditoriale

Dès qu'un cas réel PURH important est stabilisé, il doit être converti en fixture courte, en test de non-régression et en note descriptive.

---

## 11. Dépendance aux sources réelles

Les documents réels servent à comprendre. Les tests doivent en extraire des cas courts. Ne pas faire reposer la stabilité du projet sur de gros fichiers opaques.

---

## 12. Déclenchement recommandé des tests

À chaque tâche Codex significative : lancer les tests unitaires concernés, les tests d'intégration directement touchés, les tests de non-régression associés, et mentionner les tests ajoutés ou adaptés.

---

## 13. Tests minimaux pour une passe structure

Toute passe touchant la reconnaissance structurelle devrait vérifier : vrai titre reconnu, paragraphe ordinaire non promu, citation longue reconnue ou diagnostiquée, séquence poétique protégée, faux heading Word neutralisé si conflit, liste réelle conservée, liste accidentelle en poésie non conservée comme puce.
