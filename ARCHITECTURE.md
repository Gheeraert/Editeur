# ARCHITECTURE.md

## 1. Principes directeurs

- Modularité stricte.
- Logique métier hors interface.
- Dataclasses Python comme pivot réel.
- Transformations traçables.
- Diagnostics explicites.
- IA optionnelle, encadrée et désactivable.
- Validation humaine pour toute décision interprétative.

Le projet ne doit pas être compris comme une simple chaîne `DOCX auteur -> DOCX final`, mais comme une chaîne de préparation éditoriale capable de produire un état structuré, contrôlable et exportable vers Métopes / XML-TEI.

---

## 2. Pivot architectural

Le pivot réel est le modèle Python interne :

```text
Document
  -> Block
  -> InlineSpan
  -> Note
  -> Diagnostic
  -> Suggestion
  -> Transformation
  -> ProcessingReport
```

Le JSON est dérivé de ce pivot. Il sert au debug, aux fixtures, à la traçabilité et aux comparaisons de tests. Il n'est pas souverain.

---

## 3. Pipeline cible

```text
DOCX auteur
  -> import riche
  -> modèle interne
  -> extraction des faits documentaires
  -> décisions éditoriales graduées
  -> services de correction / structuration
  -> sorties :
       - JSON de contrôle
       - DOCX de relecture humaine
       - XML-TEI Métopes de production
```

Le DOCX reste une sortie de relecture. La sortie de production visée est l'XML-TEI Métopes.

---

## 4. Faits Word, indices, candidats, décisions

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
  -> transformation éventuelle
```

Le détail de cette doctrine est décrit dans `docs/EDITORIAL_DECISION_MODEL.md`.

---

## 5. Niveaux de décision éditoriale

### 5.1 Déterministe

Règles locales, explicites, testables : espaces, guillemets, siècles, abréviations, corrections sûres. Toute transformation déterministe doit être localisée, réversible et tracée.

### 5.2 Heuristique scorée

Reconnaissance probable, avec score, indices et vetos : candidat titre, citation longue, poésie, bibliographie, code, transcription linguistique.

Une heuristique doit produire :

- `score` ;
- `decision` (`ignore`, `diagnostic`, `transform`) ;
- `evidence` ;
- `veto_reasons` ;
- éventuellement `ai_candidate`.

### 5.3 IA locale encadrée

L'IA locale intervient seulement en zone grise, sur une question fermée. Elle ne réécrit pas, ne transforme pas directement et ne passe pas outre les vetos.

### 5.4 IA exploratoire ou freestyle

L'IA exploratoire est désactivée par défaut. Elle peut aider à comprendre un cas rare, mais ne doit jamais modifier automatiquement le texte source. C'est une solution de dernier recours.

---

## 6. Vetos et zones protégées

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

Exemple : une séquence poétique doit être reconnue avant les titres. Un vers isolé ne doit pas devenir `heading` parce qu'il est court, commence par une majuscule ou possède un style Word accidentel.

---

## 7. Ordre recommandé des traitements structurels

1. Importer les faits Word.
2. Identifier les zones protégées évidentes ou probables.
3. Poser les vetos structurels.
4. Calculer les candidats concurrents.
5. Appliquer les transformations déterministes sûres.
6. Produire des diagnostics pour les zones grises.
7. Soumettre éventuellement les zones grises à une IA locale encadrée.
8. Réserver l'IA exploratoire à l'analyse non automatique.

Ne jamais promouvoir un bloc en titre avant d'avoir vérifié qu'il n'appartient pas à une zone protégée.

---

## 8. Métopes : style Word vs structure TEI

Il faut distinguer :

- le style Word Métopes, utile pour la relecture et la préparation humaine ;
- la structure TEI Métopes, qui porte la sémantique documentaire de production.

Conclusion :

```text
style Word != structure éditoriale
style Word != structure TEI
```

La conversion vers Métopes doit passer par le modèle interne et par des décisions documentées.

---

## 9. Documents de référence

- `README.md`
- `SPECS.md`
- `DATA_MODEL.md`
- `docs/EDITORIAL_DECISION_MODEL.md`
- `AI_STYLE_POLICY_V1.md`
- `TEST_STRATEGY.md`
- `FIXTURES.md`
- `METOPES_MAPPING.md`
