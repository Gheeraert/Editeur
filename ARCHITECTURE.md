# Architecture

## 1. Principes directeurs

- Modularité stricte.
- Logique métier hors interface.
- Dataclasses Python comme représentation vivante du pivot.
- JSON canonique comme représentation stable, versionnée et testable du pivot.
- Transformations traçables.
- Diagnostics explicites.
- IA optionnelle, encadrée et désactivable.
- Validation humaine pour toute décision interprétative.
- Exporteurs limités à leur rôle de rendu.

Le projet ne doit pas être compris comme une simple chaîne `DOCX auteur -> DOCX final`, mais comme une chaîne de préparation éditoriale capable de produire un état structuré, contrôlable et exportable vers Métopes / XML‑TEI.

---

## 2. Pivot architectural

Le pivot réel est le modèle Python interne, avec sérialisation JSON canonique.

```text
Document
  -> Metadata
  -> Block
  -> InlineSpan
  -> Note
  -> Diagnostic
  -> Suggestion
  -> Transformation
  -> ProcessingReport
```

Le JSON est dérivé du modèle Python, mais il n'est pas un simple fichier de debug. Il constitue le **contrat sérialisé** du pivot : il doit être versionné, relisible, diffable et exploitable comme fixture.

Formule :

```text
Python = représentation vivante
JSON   = représentation contractuelle sérialisée
```

---

## 3. Pipeline cible

```text
DOCX auteur
  -> import riche
  -> extraction des faits documentaires
  -> modèle Python initial
  -> décisions éditoriales graduées
  -> canonicalisation du pivot
  -> validation des invariants Python‑JSON
  -> sorties :
       - JSON canonique de contrôle
       - DOCX de relecture humaine
       - XML‑TEI Métopes de production
       - LaTeX / HTML / PDF selon modules
```

Le DOCX reste une sortie de relecture. La sortie de production visée est l'XML‑TEI Métopes. Le JSON sert de pivot observable et testable.

---

## 4. Séparation des responsabilités

### 4.1 Importeurs

Les importeurs lisent les sources et conservent les faits matériels : styles, inlines, notes, tableaux, sauts, retraits, listes, objets utiles.

Ils peuvent signaler certains faits évidents, mais ne doivent pas confondre style source et structure éditoriale.

### 4.2 Services de décision

Les services de décision interprètent les faits source, calculent des candidats, posent des vetos, produisent diagnostics et transformations.

C'est ici que doivent vivre les heuristiques de structure : titres, citations, vers, listes, bibliographie, tableaux, code, transcriptions.

### 4.3 Canonicalisation du pivot

La canonicalisation transforme des décisions ou indices en représentation stable.

Exemple :

```text
séquence détectée comme poésie
  -> quote_block canonique
  -> quote_kind = poetry
  -> lineation = verse
  -> lignes exploitables
```

Cette étape doit empêcher les attributs flottants de devenir des vérités concurrentes.

### 4.4 Validation du pivot

La validation contrôle les invariants avant export.

Exemples :

```text
quote_kind == poetry => lineation == verse
heading => heading_level présent
lineation == verse => lignes exploitables
protected_zone == table => pas d'aplatissement silencieux
```

### 4.5 Exporteurs

Les exporteurs ne décident pas. Ils rendent.

Ils ne doivent pas redétecter les vers, titres, listes ou citations à partir de la mise en forme. Ils consomment le pivot canonicalisé.

---

## 5. Faits Word, indices, candidats, décisions

Un fichier Word ne donne pas directement des structures éditoriales fiables. Il donne des faits matériels : styles, gras, italique, retraits, puces, notes, tableaux, objets, ruptures de ligne, etc.

Ces faits doivent être traités comme des indices, non comme des vérités. Un style Word `Titre 2` peut être un vrai titre, mais aussi un vers accidentellement stylé, une légende ou un accident de mise en forme.

La chaîne de décision doit donc être :

```text
faits documentaires
  -> indices
  -> candidats concurrents
  -> conflits éventuels
  -> vetos
  -> décision ou diagnostic
  -> canonicalisation éventuelle
```

Le détail de cette doctrine est décrit dans `docs/EDITORIAL_DECISION_MODEL.md`.

---

## 6. Niveaux de décision éditoriale

### 6.1 Déterministe

Règles locales, explicites, testables : espaces, guillemets, siècles, abréviations, corrections sûres. Toute transformation déterministe doit être localisée, réversible et tracée.

### 6.2 Heuristique scorée

Reconnaissance probable, avec score, indices et vetos : candidat titre, citation longue, poésie, bibliographie, code, transcription linguistique.

Une heuristique doit produire :

- `score` ;
- `decision` (`ignore`, `diagnostic`, `transform`) ;
- `evidence` ;
- `veto_reasons` ;
- éventuellement `ai_candidate`.

### 6.3 IA locale encadrée

L'IA locale intervient seulement en zone grise, sur une question fermée. Elle ne réécrit pas, ne transforme pas directement et ne passe pas outre les vetos.

### 6.4 IA exploratoire ou freestyle

L'IA exploratoire est désactivée par défaut. Elle peut aider à comprendre un cas rare, mais ne doit jamais modifier automatiquement le texte source. C'est une solution de dernier recours.

---

## 7. Vetos et zones protégées

Certaines zones doivent être protégées avant toute transformation concurrente :

- poésie ;
- citation ancienne ;
- code informatique ;
- transcription linguistique ;
- tableau ;
- formule ;
- bibliographie ;
- légende.

Une zone protégée peut bloquer :

- une promotion en titre ;
- une transformation en liste ;
- une correction typographique agressive ;
- une suggestion stylistique ;
- une normalisation d'espaces ou de ponctuation.

Une zone protégée ne remplace pas une structure canonique. Elle signale un régime de prudence et de veto.

---

## 8. Métopes : style Word vs structure TEI

Il faut distinguer :

- le style Word Métopes, utile pour la relecture et la préparation humaine ;
- la structure TEI Métopes, qui porte la sémantique documentaire de production ;
- le pivot Python‑JSON, qui doit gouverner les deux.

Conclusion :

```text
style Word != structure éditoriale
style Word != structure TEI
rendu DOCX correct != pivot validé
```

La conversion vers Métopes doit passer par le modèle interne et par des décisions documentées.

---

## 9. Règle pour les branches de refactorisation

Le développement reste incrémental, mais une refactorisation de fond est légitime lorsque le contrat de données est instable.

Dans ce cas :

- créer une branche dédiée ;
- documenter les invariants avant de coder ;
- ajouter des tests de pivot avant de réparer les sorties ;
- supprimer les heuristiques locales concurrentes ;
- conserver les comportements stabilisés par fixtures.

---

## 10. Documents de référence

- `README.md`
- `SPECS.md`
- `DATA_MODEL.md`
- `docs/PIVOT_JSON_CONTRACT.md`
- `docs/EXPORTERS_CONTRACT.md`
- `docs/EDITORIAL_DECISION_MODEL.md`
- `docs/EDITORIAL_PIPELINE.md`
- `AI_STYLE_POLICY_V1.md`
- `TEST_STRATEGY.md`
- `FIXTURES.md`
- `METOPES_MAPPING.md`
