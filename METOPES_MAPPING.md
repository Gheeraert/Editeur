# Mapping Métopes

## Statut de ce document

Ce document est un **cadre provisoire**.

Il doit être complété à partir :

- d'exemples XML Métopes réels ;
- des contraintes effectivement retenues dans le projet ;
- des usages réels des PURH ;
- du contrat du pivot Python‑JSON.

Il ne prétend pas décrire toute la TEI ni tout Métopes.

---

## 1. Objet

Décrire les correspondances entre les structures canoniques du pivot et les structures XML attendues dans le cadre Métopes / TEI retenu.

Le mapping ne part pas directement du fichier Word auteur. Il part du pivot validé.

```text
pivot Python‑JSON validé -> XML‑TEI Métopes
```

---

## 2. Principe

Le projet ne doit pas partir de la TEI abstraite en général, mais du **sous-ensemble réellement utilisé**.

Il faut donc documenter :

- les structures fréquentes ;
- les conventions locales ;
- les cas non couverts ;
- les zones d'ambiguïté ;
- les invariants du pivot nécessaires avant export.

---

## 3. Règle architecturale

```text
style Word Métopes != structure TEI Métopes
```

Un style Word `TEI_verse`, `TEI_quote`, `Heading 2` ou autre peut être un indice source, un choix de rendu ou un produit de stylage. Il ne doit pas être la source de vérité structurelle.

La source de vérité est le pivot canonicalisé.

---

## 4. Structures documentaires à cartographier

### 4.1 Titres et intertitres

À préciser :

- comment distinguer titre principal, titre de chapitre, intertitre ;
- quelles balises sont utilisées ;
- quels attributs sont requis ;
- quel champ du pivot porte le niveau (`heading_level`).

Invariant pivot :

```text
block_type = heading
semantic_role = heading
heading_level présent et valide
```

### 4.2 Paragraphes

À documenter :

- balise attendue ;
- gestion des alinéas si pertinente ;
- cas de paragraphes spéciaux.

Invariant pivot :

```text
block_type = paragraph
semantic_role = paragraph
```

### 4.3 Citations en prose

À documenter :

- citation courte ;
- citation en bloc ;
- citations imbriquées ;
- italiques ou guillemets internes.

Invariant pivot :

```text
block_type = quote_block
quote_kind = prose
lineation = prose
```

### 4.4 Citations en vers

À documenter prioritairement.

Sortie XML cible probable :

```xml
<cit>
  <quote>
    <lg>
      <l>Premier vers</l>
      <l>Deuxième vers</l>
    </lg>
  </quote>
</cit>
```

Invariant pivot minimal :

```text
block_type = quote_block
quote_kind = poetry
lineation = verse
lignes exploitables
```

À ne pas faire :

```text
si style Word == TEI_verse, produire directement <lg>/<l>
```

Le style Word doit être transformé en décision canonique avant export.

### 4.5 Notes

À documenter :

- balisage des appels ;
- structure des notes ;
- ancrage ;
- ordre attendu.

Invariant pivot :

```text
InlineSpan(kind=note_call) lié à Note.note_id
```

### 4.6 Listes

À documenter :

- listes simples ;
- listes numérotées ;
- hiérarchie éventuelle ;
- distinction entre liste réelle et accident de puce.

Invariant pivot :

```text
block_type = list_item ou structure de liste dédiée
```

### 4.7 Tableaux

À documenter :

- mapping minimal vers `<table>`, `<row>`, `<cell>` ;
- conservation de l'ordre ;
- gestion des tableaux complexes ;
- fallback diagnostiqué.

Invariant pivot :

```text
block_type = table
structure tabulaire conservée ou OOXML protégé
```

### 4.8 Bibliographie

À documenter :

- niveau de structuration attendu ;
- forme minimale acceptable ;
- dépendance éventuelle au CSL ou à d'autres normalisations.

### 4.9 Annexes / figures / légendes

À documenter si elles entrent dans le périmètre initial.

---

## 5. Tableau de mapping à constituer

| Structure pivot | Invariant pivot | Sortie XML visée | Attributs requis | Cas limites | Validation humaine |
|---|---|---|---|---|---|
| `heading` | `heading_level` | à compléter | niveau | faux titre | selon score |
| `paragraph` | rôle paragraphe | `<p>` probable | aucun | paragraphe spécial | non |
| citation prose | `quote_kind=prose` | `<cit><quote>` probable | à préciser | citation imbriquée | selon cas |
| citation vers | `quote_kind=poetry`, `lineation=verse` | `<cit><quote><lg><l>` | lignes | chronologie faussement poétique | oui si ambigu |
| table | structure conservée | `<table><row><cell>` | lignes/cellules | tableaux fusionnés | oui |

---

## 6. Niveau de confiance des mappings

Tous les mappings ne relèvent pas du même régime.

### Niveau 1 — Sûr

Correspondance stable et documentée.

### Niveau 2 — Probable

Correspondance fréquente, mais à confirmer.

### Niveau 3 — Ambigu

Cas nécessitant validation humaine.

### Niveau 4 — Fallback diagnostiqué

Le pivot contient une structure que le mapping actuel ne sait pas encore représenter correctement. L'export doit signaler explicitement la limite.

---

## 7. Ce qu'il faudra extraire des premiers XML réels

Pour chaque fichier XML fourni :

- lister les balises réellement présentes ;
- identifier les structures récurrentes ;
- noter les attributs réellement utilisés ;
- repérer les écarts entre théorie et pratique ;
- isoler 5 à 10 cas exemplaires comme fixtures ;
- rattacher chaque structure XML à un invariant du pivot.

---

## 8. Rapport avec le module de visualisation

Le mapping XML n'est pas validé seulement par conformité structurelle. Il l'est aussi par le rendu :

- HTML ;
- PDF ;
- éventuellement LaTeX.

Mais un rendu correct ne suffit pas. Il faut vérifier que le pivot, le XML et le rendu sont cohérents.

---

## 9. Limites actuelles

Tant que les exemples XML réels n'ont pas été fournis :

- ne pas figer toutes les balises ;
- ne pas promettre de conversion complète ;
- ne pas multiplier les structures sans base documentaire ;
- ne pas compenser un pivot incomplet par des heuristiques d'export.

---

## 10. Priorité documentaire

Les premières pièces à analyser sont :

1. deux XML Métopes réels ;
2. un rendu HTML ou PDF associé ;
3. éventuellement une note locale sur les conventions d'encodage utilisées ;
4. les JSON pivot correspondant aux mêmes extraits.
