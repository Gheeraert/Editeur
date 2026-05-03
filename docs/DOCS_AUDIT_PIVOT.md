# Audit documentaire — stabilisation du pivot Python‑JSON

## 1. Objet de cette passe

Cette passe documentaire prépare une refactorisation de fond du projet PURH Editorial Studio.

Elle ne vise pas à corriger localement un export défaillant. Elle vise à établir une règle d'architecture :

```text
les exports DOCX, XML‑TEI et LaTeX ne doivent être que des représentations du pivot Python‑JSON.
```

Autrement dit : si le DOCX, le XML et le LaTeX divergent, le premier suspect n'est pas l'exporteur, mais l'absence d'un contrat de données pivot assez stable.

---

## 2. Constat documentaire

La documentation existante contient déjà des principes solides :

- distinction entre faits Word et structures éditoriales ;
- rôle central des dataclasses Python ;
- prudence éditoriale ;
- zones protégées ;
- IA encadrée ;
- nécessité de tests par fixtures.

Mais elle comporte une ambiguïté critique : le JSON y est souvent présenté comme un simple dérivé du modèle Python, utile au debug, aux fixtures et à la traçabilité. Cette formulation est exacte techniquement, mais insuffisante pour gouverner la chaîne.

Le bon modèle est le suivant :

```text
Python = représentation vivante du pivot dans le code
JSON = représentation sérialisée, stable, versionnée et testable du même pivot
```

Le JSON n'est pas « souverain » contre Python. Mais il doit être **normatif comme contrat d'échange et de test**.

---

## 3. Problème révélé par les vers

Le défaut observé sur les vers ne doit pas être traité comme un simple défaut d'export XML.

Le symptôme :

```text
un bloc reconnu comme versifié peut être bien rendu dans le DOCX,
mais être exporté en XML comme citation prose, sans <lg>/<l>.
```

La cause architecturale :

```text
plusieurs modules possèdent encore leur propre définition locale de la poésie.
```

Un exporteur peut lire `quote_kind`, un autre `protected_zone`, un troisième un style Métopes. Le système n'a donc pas encore un invariant unique du type :

```text
ce bloc est une citation en vers, avec des lignes de vers exploitables.
```

Le cas des vers devient ainsi un cas exemplaire : tant que le pivot ne dit pas clairement ce qu'est un bloc poétique, les sorties peuvent diverger.

---

## 4. Doctrine retenue

La refactorisation devra suivre quatre principes.

### 4.1 L'amont décide

Les modules d'import, de normalisation, de reconnaissance structurelle et d'arbitrage produisent les décisions éditoriales.

Ils peuvent utiliser des faits Word, des heuristiques, des scores, des vetos, des diagnostics et, en dernier recours, une IA locale encadrée.

### 4.2 Le pivot enregistre

Une décision validée ou appliquée doit être inscrite dans le modèle Python et dans sa représentation JSON de manière stable.

Exemple : une citation en vers ne doit pas être seulement un `quote_block` avec un attribut flottant. Elle doit porter une sémantique canonique exploitable par tous les rendus.

### 4.3 L'aval représente

Les exporteurs DOCX, XML‑TEI, LaTeX, HTML ou PDF ne doivent pas redétecter les structures.

Ils reçoivent le pivot validé et produisent une représentation dans leur format cible.

### 4.4 Les divergences deviennent des diagnostics

Si un exporteur reçoit un bloc incomplet ou incohérent, il ne doit pas le réparer silencieusement. Il doit produire un diagnostic ou échouer explicitement selon le niveau de gravité.


## 4.5 Point de vigilance après la première passe Codex

La première passe de refactorisation a introduit une couche sémantique, un canonicalizer, un validator et des tests. La direction est bonne, mais elle révèle un risque précis : confondre une sémantique **reconstructible** avec une sémantique **inscrite** dans le pivot.

Cas critique :

```text
read_block_semantics() peut reconstruire une poésie depuis quote_kind=poetry
mais block.attributes["semantic"] est absent
```

Dans ce cas, le pivot JSON n'est pas encore conforme. Il ne suffit pas que le code sache retrouver l'intention : la décision doit être écrite dans le champ canonique sérialisé, afin que le JSON soit diffable, testable et relisible sans dépendre d'une heuristique cachée.

Conclusion opérationnelle : le canonicalizer doit comparer le contenu effectivement stocké dans le JSON, et non seulement la sémantique normalisée obtenue après lecture de compatibilité. Si `attributes["semantic"]` manque, il doit l'écrire et produire une transformation traçable.

---

## 5. Points à changer dans la documentation

### 5.1 `README.md`

À modifier : présenter le projet comme une chaîne gouvernée par un pivot Python‑JSON, et non comme une chaîne DOCX avec sorties secondaires.

À ajouter : règle « les exporteurs ne corrigent pas le document ».

### 5.2 `ARCHITECTURE.md`

À modifier : préciser que le JSON est la projection stable, versionnée et testable du modèle Python.

À ajouter : séparation stricte entre import, décision, canonicalisation, validation du pivot et rendu.

### 5.3 `DATA_MODEL.md`

À modifier fortement : documenter le contrat pivot, les invariants minimaux et les catégories d'attributs.

À ajouter : `schema_version`, `pipeline_stage`, `semantic_role`, `lineation`, `lines`, `source`, `layout`, `rendering`, `decisions`, même si certains champs seront introduits progressivement.

### 5.4 `SPECS.md`

À modifier : expliciter que la réussite du projet se mesure à la stabilité du pivot et à l'accord des exports, non à la vraisemblance visuelle d'une seule sortie.

### 5.5 `TEST_STRATEGY.md`

À modifier : ajouter des tests d'invariants du pivot, de round‑trip JSON et de cohérence entre exports.

### 5.6 `FIXTURES.md`

À modifier : créer une famille de fixtures `pivot_contract/` et renforcer les fixtures poésie.

### 5.7 `METOPES_MAPPING.md`

À modifier : rappeler que Métopes est une projection du pivot ; les styles Word Métopes ne peuvent pas être la source de vérité structurelle.

### 5.8 `docs/EDITORIAL_PIPELINE.md`

À modifier fortement : insérer une étape explicite de canonicalisation et de validation du pivot avant tout export.

### 5.9 `docs/EDITORIAL_DECISION_MODEL.md`

À modifier : distinguer décision éditoriale, annotation source, zone protégée, représentation canonique et rendu.

### 5.10 Nouveaux fichiers à ajouter

- `docs/PIVOT_JSON_CONTRACT.md` : contrat du pivot Python‑JSON ;
- `docs/EXPORTERS_CONTRACT.md` : règles imposées aux exporteurs ;
- `docs/DOCS_AUDIT_PIVOT.md` : le présent audit documentaire.

---

## 6. Ce qui doit guider Codex après cette passe

Codex ne doit pas recevoir une demande du type :

```text
corrige l'export XML des vers
```

mais :

```text
stabilise le contrat pivot Python‑JSON, ajoute les invariants nécessaires,
puis adapte les exporteurs pour qu'ils représentent ce contrat sans heuristique locale.
```

Les branches propres servent précisément à cela : isoler une refactorisation conceptuelle, supprimer les scories, reconstruire les invariants, puis seulement rétablir les sorties.


## 7. Consigne de consolidation pour la suite

La prochaine passe Codex ne doit pas élargir le périmètre. Elle doit consolider le contrat déjà posé :

1. `PivotCanonicalizer` doit écrire explicitement `block.attributes["semantic"]` dès qu'une décision canonique est absente ou divergente dans le JSON.
2. Les prédicats utilisés par les exporteurs doivent lire la sémantique canonique stockée, non les clés legacy.
3. Les clés `quote_kind`, `lineation`, `protected_zone`, `metopes_style` et les styles Word restent des indices ou des supports de migration, pas des sources de vérité aval.
4. Un test doit vérifier qu'un bloc legacy poésie devient explicitement canonique après canonicalization.
5. Un autre test doit vérifier qu'un export direct sur bloc legacy non canonicalisé ne constitue pas une preuve de conformité du pivot.

Formule courte :

```text
ce qui est seulement inférable n'est pas encore un pivot ;
ce qui est pivot doit être écrit, versionné et testé.
```
