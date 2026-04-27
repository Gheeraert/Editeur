# METOPES_MAPPING.md

## Statut de ce document

Ce document est un **cadre provisoire**.
Il doit être complété à partir :
- d'exemples XML Métopes réels ;
- des contraintes effectivement retenues dans le projet ;
- des usages réels des PURH.

Il ne prétend pas décrire toute la TEI ni tout Métopes.

---

## 1. Objet

Décrire les correspondances entre éléments du manuscrit préparé et structures XML attendues dans le cadre Métopes / TEI retenu.

---

## 2. Principe

Le projet ne doit pas partir de la TEI abstraite en général, mais du **sous-ensemble réellement utilisé**.

Il faut donc documenter :
- les structures fréquentes ;
- les conventions locales ;
- les cas non couverts ;
- les zones d'ambiguïté.

---

## 3. Structures documentaires à cartographier

## 3.1 Titres et intertitres
À préciser :
- comment distinguer titre principal, titre de chapitre, intertitre ;
- quelles balises sont utilisées ;
- quelles métadonnées ou attributs sont requis.

## 3.2 Paragraphes
À documenter :
- balise attendue ;
- gestion des alinéas si pertinente ;
- cas de paragraphes spéciaux.

## 3.3 Citations
À documenter :
- citation courte ;
- citation en bloc ;
- citations imbriquées ;
- italiques ou guillemets internes.

## 3.4 Notes
À documenter :
- balisage des appels ;
- structure des notes ;
- ancrage ;
- ordre attendu.

## 3.5 Listes
À documenter :
- listes simples ;
- listes numérotées ;
- hiérarchie éventuelle.

## 3.6 Bibliographie
À documenter :
- niveau de structuration attendu ;
- forme minimale acceptable ;
- dépendance éventuelle au CSL ou à d'autres normalisations.

## 3.7 Annexes / figures / légendes
À documenter si elles entrent dans le périmètre initial.

---

## 4. Tableau de mapping à constituer

Le tableau ci-dessous devra être rempli à partir des exemples réels.

| Élément source | Signal de reconnaissance | Sortie XML visée | Attributs requis | Cas limites | Validation humaine |
|---|---|---|---|---|---|
| Titre de chapitre | style ou motif | à compléter | à compléter | à compléter | oui/non |

---

## 5. Niveau de confiance des mappings

Tous les mappings ne relèvent pas du même régime.

### Niveau 1 — Sûr
Correspondance stable et documentée.

### Niveau 2 — Probable
Correspondance fréquente, mais à confirmer.

### Niveau 3 — Ambigu
Cas nécessitant validation humaine.

---

## 6. Ce qu'il faudra extraire des premiers XML réels

Pour chaque fichier XML fourni :
- lister les balises réellement présentes ;
- identifier les structures récurrentes ;
- noter les attributs réellement utilisés ;
- repérer les écarts entre théorie et pratique ;
- isoler 5 à 10 cas exemplaires comme fixtures.

---

## 7. Rapport avec le module de visualisation

Le mapping XML n'est pas validé seulement par conformité structurelle.
Il l'est aussi par le rendu :
- HTML ;
- PDF.

Un mapping n'est réellement satisfaisant que si les sorties produites rendent lisible la structure voulue.

---

## 8. Limites actuelles

Tant que les exemples XML réels n'ont pas été fournis :
- ne pas figer les balises ;
- ne pas promettre de conversion complète ;
- ne pas multiplier les structures sans base documentaire.

---

## 9. Priorité documentaire

Les premières pièces à analyser sont :
1. deux XML Métopes réels ;
2. un rendu HTML ou PDF associé ;
3. éventuellement une note locale sur les conventions d'encodage utilisées.
