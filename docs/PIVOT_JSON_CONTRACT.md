# Contrat du pivot Python‑JSON

## 1. Statut

Ce document définit le contrat central du projet PURH Editorial Studio.

Le pivot est une double représentation d'un même état documentaire :

```text
Python dataclasses  <=>  JSON canonique
```

- Les dataclasses Python sont la représentation vivante utilisée par le code.
- Le JSON est la représentation sérialisée, stable, versionnée, diffable, testable et échangeable.

Le JSON n'est pas un export au même titre que DOCX, XML‑TEI ou LaTeX. Il est la forme contrôlable du pivot.

---

## 2. Principe fondamental

```text
Un exporteur ne doit jamais inventer la structure qu'il rend.
```

Les décisions structurelles doivent être prises avant l'export et inscrites dans le pivot. Les sorties DOCX, XML‑TEI, LaTeX, HTML et PDF ne sont que des représentations spécialisées du pivot.

Conséquence :

```text
si une sortie est fausse, vérifier d'abord le pivot ;
si le pivot est faux ou incomplet, corriger l'amont ;
si le pivot est juste, corriger seulement le renderer.
```

---

## 3. Versionnement du contrat

Tout JSON pivot doit comporter une version de schéma.

Exemple minimal :

```json
{
  "schema_version": "pivot-1.0",
  "document_id": "doc_001",
  "source": {...},
  "metadata": {...},
  "blocks": [...],
  "notes": [...],
  "report": {...}
}
```

Règles :

- toute rupture de structure augmente la version ;
- toute nouvelle clé facultative doit être documentée ;
- les tests doivent préciser la version attendue ;
- une fonction `from_json` doit reconstruire le modèle Python sans perte critique.

---

## 4. Séparation des couches d'information

Le pivot doit éviter de tout déposer dans un dictionnaire `attributes` non typé.

À terme, chaque bloc devrait distinguer au moins :

```text
source      : faits issus du document source
layout      : indices de mise en page ou de présentation
semantic    : décision éditoriale canonique
rendering   : informations de rendu ou de projection
processing  : traces, scores, règles, vetos, diagnostics
```

Une période transitoire peut conserver `attributes`, mais les clés doivent être classées et documentées.

---

## 5. Faits source

Les faits source décrivent ce qui a été observé dans le document d'entrée.

Exemples :

```json
{
  "source": {
    "format": "docx",
    "style_id": "Titre2",
    "style_name": "Titre 2",
    "all_runs_bold": true,
    "all_runs_italic": false,
    "num_id": null,
    "numbering_level": null,
    "has_page_break_before": false,
    "has_line_breaks": true
  }
}
```

Un fait source n'est pas une décision.

---

## 6. Indices de mise en page

Les indices de mise en page aident à décider, mais ne doivent pas gouverner directement les exports.

Exemples :

```json
{
  "layout": {
    "ind_left": 720,
    "ind_first_line": 0,
    "space_before": 240,
    "space_after": 120,
    "blank_before": true,
    "blank_after": false,
    "average_line_length": 44
  }
}
```

---

## 7. Sémantique canonique

La sémantique canonique exprime ce que le système décide que le bloc est.

Exemple de paragraphe ordinaire :

```json
{
  "block_type": "paragraph",
  "semantic": {
    "role": "paragraph"
  }
}
```

Exemple de titre :

```json
{
  "block_type": "heading",
  "semantic": {
    "role": "heading",
    "heading_level": 2
  }
}
```

Exemple de citation en prose :

```json
{
  "block_type": "quote_block",
  "semantic": {
    "role": "quote",
    "quote_kind": "prose",
    "lineation": "prose"
  }
}
```

Exemple de citation en vers :

```json
{
  "block_type": "quote_block",
  "semantic": {
    "role": "quote",
    "quote_kind": "poetry",
    "lineation": "verse"
  },
  "lines": [
    {"text": "Premier vers", "inlines": [...]},
    {"text": "Deuxième vers", "inlines": [...]}
  ]
}
```


### 7.1 Sémantique stockée et sémantique inférée

Le contrat distingue strictement deux choses :

```text
sémantique canonique explicitement stockée dans le pivot
≠
sémantique reconstruite à la volée depuis des clés anciennes ou des indices source
```

Une fonction de compatibilité peut, pendant une phase de migration, **lire** d'anciens marqueurs comme `quote_kind`, `lineation`, `protected_zone`, `metopes_style`, `style_name` ou un style Word `TEI_verse`. Cette lecture peut aider le canonicalizer à comprendre un ancien état du modèle.

Mais un bloc n'est conforme au pivot canonique que lorsque la décision sémantique est **écrite explicitement** dans le champ stable prévu par le contrat. Dans l'implémentation transitoire actuelle, ce champ peut être :

```json
{
  "attributes": {
    "semantic": {
      "role": "quote",
      "quote_kind": "poetry",
      "lineation": "verse",
      "lines": ["Premier vers", "Deuxième vers"]
    }
  }
}
```

Les clés legacy conservées à côté de ce champ peuvent servir à la compatibilité ascendante, aux diagnostics ou aux migrations. Elles ne doivent pas être la source de vérité des exporteurs.

Conséquence : si une fonction `read_block_semantics()` peut reconstruire une poésie depuis `quote_kind="poetry"`, mais que `attributes["semantic"]` est absent, le pivot JSON n'est pas encore conforme. Le rôle du canonicalizer est alors d'écrire la sémantique canonique manquante et de tracer cette transformation.

---

## 8. Contrat minimal transitoire pour la poésie

En attendant l'introduction éventuelle d'un objet `lines` pleinement typé, un bloc poétique doit porter une sémantique canonique explicite. Le format transitoire recommandé est :

```json
{
  "block_type": "quote_block",
  "text": "Premier vers\nDeuxième vers",
  "attributes": {
    "semantic": {
      "role": "quote",
      "quote_kind": "poetry",
      "lineation": "verse",
      "lines": ["Premier vers", "Deuxième vers"]
    },
    "protected_zone": "poetry"
  }
}
```

Le format suivant est seulement un état legacy à migrer, non un pivot canonique conforme :

```json
{
  "block_type": "quote_block",
  "text": "Premier vers\nDeuxième vers",
  "attributes": {
    "quote_kind": "poetry",
    "lineation": "verse",
    "protected_zone": "poetry"
  }
}
```

Dans ce cas, le canonicalizer doit écrire `attributes["semantic"]` avant tout export fiable.

Invariants :

```text
semantic.quote_kind == poetry  => semantic.lineation == verse
semantic.lineation == verse    => le bloc possède des lignes exploitables
protected_zone poetry          => le bloc ne peut pas être promu en heading
```

Un exporteur ne doit pas décider qu'un bloc est poétique à partir de sa seule apparence ni à partir des seules clés legacy. Il peut seulement représenter une sémantique canonique déjà stockée, ou signaler un pivot incohérent.

---

## 9. Zones protégées

Une zone protégée n'est pas une structure suffisante. Elle est un mécanisme de veto.

Exemple :

```json
{
  "processing": {
    "protected_zone": {
      "type": "poetry",
      "score": 0.91,
      "rule_id": "structure.poetry.sequence",
      "blocks": ["b12", "b13", "b14"]
    }
  }
}
```

Une zone protégée peut empêcher certaines transformations, mais elle ne remplace pas la sémantique canonique.

Ainsi :

```text
protected_zone = poetry
```

ne suffit pas à produire un `<lg>` en XML. Le bloc doit être canonicalisé comme citation en vers avant l'export.

---

## 10. Décisions et diagnostics

Toute décision structurelle significative doit être associée à une trace.

Exemple :

```json
{
  "decision": {
    "rule_id": "structure.poetry.sequence",
    "category": "poetry",
    "score": 0.93,
    "decision": "transform",
    "evidence": {
      "line_count": 4,
      "average_line_length": 38,
      "homogeneous_lengths": true,
      "source_styles": ["Normal", "Titre2"]
    },
    "veto_reasons": []
  }
}
```

Si une décision reste incertaine, le pivot doit conserver le diagnostic plutôt que produire une transformation silencieuse.

---

## 11. Invariants généraux du pivot

### 11.1 Identifiants

Chaque bloc, note, transformation, diagnostic et suggestion possède un identifiant stable.

### 11.2 Round‑trip JSON

Le test suivant doit être possible :

```text
Python Document -> JSON -> Python Document -> JSON
```

Le résultat doit être stable pour les champs documentés du contrat.

### 11.3 Pas de structure implicite dans les exports

Aucun exporteur ne doit transformer un paragraphe en titre, en vers, en liste ou en tableau par heuristique locale.

### 11.4 Le canon doit être stocké, non seulement reconstructible

La conformité du pivot se vérifie sur le JSON réellement sérialisé. Une sémantique seulement reconstructible par une fonction de lecture ou par compatibilité legacy ne suffit pas.

Test minimal attendu :

```text
bloc legacy quote_kind=poetry, sans attributes.semantic
  -> canonicalizer
  -> attributes.semantic existe dans le JSON
  -> exporteurs lisent attributes.semantic, non les clés legacy
```

---

### 11.5 Cohérence de rendu

Si le pivot dit qu'un bloc est une citation en vers :

- le DOCX doit appliquer le style ou rendu de vers ;
- le XML‑TEI doit produire `<cit><quote><lg><l>...` ;
- le LaTeX doit produire la forme versifiée retenue ;
- les tests doivent vérifier l'accord de ces sorties.

### 11.6 Diagnostic plutôt que réparation silencieuse

Un exporteur qui reçoit un état incohérent doit produire un diagnostic, lever une erreur contrôlée ou utiliser un fallback explicitement marqué. Il ne doit pas corriger silencieusement le pivot.

---

## 12. Invariants minimaux par type de bloc

| Type canonique | Champs requis | Interdictions |
|---|---|---|
| `paragraph` | texte ou inlines | pas de `heading_level` actif |
| `heading` | `heading_level` | ne doit pas appartenir à une zone protégée concurrente |
| `quote_block` prose | `quote_kind=prose`, `lineation=prose` | pas de `<lg>/<l>` en XML |
| `quote_block` poetry | `quote_kind=poetry`, `lineation=verse`, lignes exploitables | pas de rendu prose en XML |
| `table` | modèle tabulaire ou OOXML conservé | pas d'aplatissement sans diagnostic |
| `bibliography_item` | texte brut au minimum | pas de correction typographique agressive sans règle dédiée |
| `code_block` | texte brut ou inlines | pas de typographie française ordinaire |

---

## 13. Politique d'évolution

La refactorisation peut être progressive.

Ordre recommandé :

1. documenter les clés actuelles réellement utilisées ;
2. ajouter `schema_version` au JSON ;
3. ajouter `from_json` et tests de round‑trip ;
4. introduire les prédicats canoniques dans le modèle, pas dans les exporteurs ;
5. ajouter la validation du pivot avant export ;
6. déplacer les heuristiques locales des exporteurs vers les services de décision ;
7. réduire progressivement l'usage de `attributes` pour les décisions stables.

---

## 14. Formule courte

```text
Le pivot n'est pas une étape technique : c'est le lieu où le document devient éditorialement explicite.
```
