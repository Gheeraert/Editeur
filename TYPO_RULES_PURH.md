# TYPO_RULES_PURH.md

## Statut de ce document

Ce fichier est un **gabarit de travail**.
Il doit être complété et corrigé dès dépôt du guide typographique réel des PURH.

Aucune règle locale ne doit être considérée comme définitive tant qu'elle n'est pas adossée à une source interne validée.

---

## 1. Objet

Recenser les règles orthotypographiques et micro-éditoriales nécessaires au module déterministe.

Le but n'est pas de réécrire un traité général de typographie, mais de documenter :
- les règles réellement appliquées aux PURH ;
- leurs variantes éventuelles ;
- les cas de tolérance ;
- les cas qui relèvent d'une décision humaine.

---

## 2. Format recommandé pour chaque règle

Pour chaque règle, documenter :

- **Rule ID**
- **Titre bref**
- **Description**
- **Exemple fautif**
- **Exemple attendu**
- **Niveau**
  - diagnostic seul
  - correction locale proposée
  - abstention
- **Source**
  - guide PURH
  - feuille de style
  - pratique éditoriale observée
- **Remarques / exceptions**

---

## 3. Familles de règles à documenter

## 3.1 Espaces
À préciser selon les usages PURH :
- espace avant `: ; ? !` ;
- espace avant et après guillemets français ;
- espaces insécables ;
- doubles espaces ;
- espaces autour des appels de note ;
- espaces avant unités, pourcentages, numéros, etc.

### Exemple de fiche
- Rule ID : `purh.spacing.colon`
- Titre : Espace avant les deux-points
- Description : Définir si les PURH exigent une espace insécable avant `:`.
- Exemple fautif : `Voici: un cas`
- Exemple attendu : `Voici : un cas`
- Niveau : correction locale proposée
- Source : à renseigner

---

## 3.2 Guillemets
À documenter :
- guillemets français ;
- usage des guillemets anglais en second niveau ;
- espaces internes ;
- ponctuation relative aux guillemets ;
- exceptions dans les citations spécialisées.

---

## 3.3 Ponctuation
À documenter :
- virgule ;
- point-virgule ;
- deux-points ;
- ponctuation de phrase ;
- ponctuation en présence d'appels de note ;
- répétitions de signes ;
- ponctuation après italique ou citation.

---

## 3.4 Italiques
À documenter :
- titres d'œuvres ;
- mots étrangers ;
- emploi savant ;
- exclusions ;
- cas où l'italique relève d'un choix d'auteur à préserver.

---

## 3.5 Appels de note
À documenter :
- position par rapport à la ponctuation ;
- formes permises ;
- numérotation ;
- cohérence de placement.

---

## 3.6 Sigles, abréviations, siècles, numéros
À documenter :
- formes attendues pour les siècles ;
- usage de `n°`, `p.`, `t.`, `vol.`, etc. ;
- capitalisation ;
- espaces.

---

## 3.7 Références bibliographiques dans le texte
À documenter si pertinent :
- style auteur-date ou autre ;
- usage des parenthèses ;
- ponctuation ;
- abréviations récurrentes.

---

## 3.8 Titres et intertitres
À documenter :
- casse ;
- numérotation ;
- ponctuation finale ;
- hiérarchie.

---

## 4. Cas à ne pas automatiser sans source claire

Ne pas automatiser d'emblée :
- normalisation forte des citations anciennes ;
- choix disciplinaires en sciences humaines ;
- usages d'auteur délibérés ;
- traitement bibliographique complexe ;
- décisions de style de collection.

---

## 5. Ce qu'il faudra ajouter dès réception des documents PURH

### Pièces attendues
- guide typographique interne ;
- feuille de style éditoriale ;
- recommandations aux auteurs ;
- exemples de correction maison.

### Travail à faire
- transformer chaque règle en fiche exploitable ;
- attribuer un `rule_id` stable ;
- décider le niveau d'automatisation ;
- fabriquer les fixtures correspondantes.

---

## 6. Échelle d'automatisation recommandée

### Niveau 1 — Diagnostic seul
Le système signale, sans proposer de correction automatique.

### Niveau 2 — Correction locale proposée
Le système propose un remplacement simple, réversible et sûr.

### Niveau 3 — Abstention
Le système ne traite pas automatiquement et renvoie à la validation humaine.

---

## 7. Annexe à constituer plus tard

Ajouter à terme un tableau de synthèse :

| Rule ID | Famille | Diagnostic | Correction locale | Source validée | Fixtures |
|---|---|---|---|---|---|

Ce tableau servira de feuille de route de l'implémentation.
