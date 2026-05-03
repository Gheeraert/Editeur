# PURH Editorial Studio

Chaîne modulaire de préparation éditoriale pour les Presses universitaires de Rouen et du Havre (PURH).

---

## 1. Philosophie générale

Le projet n'est pas une simple chaîne :

```text
DOCX auteur -> DOCX corrigé
```

Il vise une chaîne éditoriale complète, gouvernée par un pivot explicite :

```text
DOCX auteur
  -> import riche
  -> modèle pivot Python‑JSON
  -> diagnostics / corrections / structuration
  -> validation du pivot
  -> sorties multiples :
       1) JSON canonique de contrôle
       2) DOCX de relecture humaine
       3) XML‑TEI Métopes de production
       4) LaTeX / HTML / PDF selon les besoins
```

Le pivot est constitué par les dataclasses Python (`Document`, `Block`, `InlineSpan`, `Note`, `Diagnostic`, `Suggestion`, `Transformation`, `ProcessingReport`) et par leur sérialisation JSON canonique.

Le JSON n'est pas un simple export secondaire : il est la représentation stable, versionnée, diffable et testable du pivot.

---

## 2. Principe architectural majeur

```text
Les exports ne corrigent pas le document. Ils représentent le pivot.
```

Les décisions éditoriales doivent être prises en amont, inscrites dans le modèle pivot, puis validées. Les exporteurs DOCX, XML‑TEI, LaTeX, HTML ou PDF ne doivent pas redétecter localement les structures.

Si une sortie est incorrecte, l'analyse doit suivre cet ordre :

1. le pivot Python‑JSON est-il correct ?
2. les invariants du pivot sont-ils respectés ?
3. le mapping vers la sortie cible est-il correct ?
4. le renderer est-il fautif ?

Un DOCX visuellement correct ne suffit donc pas à prouver que le modèle est juste. Le JSON pivot et les tests d'invariants font foi pour le développement.

---

## 3. Problème traité

Un manuscrit auteur n'est jamais une structure éditoriale propre. Un fichier Word contient des faits matériels : styles, gras, italique, retraits, puces, notes, tableaux, citations, accidents de mise en forme.

Ces faits peuvent être utiles, mais ils peuvent aussi mentir. Un paragraphe Word stylé comme un titre peut être un vrai titre, mais aussi un vers accidentellement stylé, une ligne de poésie devenue puce, une légende, une référence ou un fragment de transcription.

Le projet distingue donc :

```text
fait matériel -> indice -> candidat éditorial -> décision -> canonicalisation -> export
```

Cette logique est décrite dans `docs/EDITORIAL_DECISION_MODEL.md`.

Le contrat du pivot est décrit dans `docs/PIVOT_JSON_CONTRACT.md`.

Le contrat des exporteurs est décrit dans `docs/EXPORTERS_CONTRACT.md`.

---

## 4. Régimes d'action

### 4.1 Déterministe

Règles locales, explicites, testables : espaces typographiques, guillemets, appels de notes, siècles, abréviations, corrections locales sûres.

### 4.2 Heuristique scorée

Détection de structures probables, avec score, justification et vetos : titre probable, citation longue, séquence poétique, bibliographie, code, transcription linguistique.

### 4.3 IA locale encadrée

L'IA locale ne doit intervenir qu'en zone grise, sur une question fermée et courte. Elle ne décide pas souverainement et ne passe pas outre les vetos.

### 4.4 IA exploratoire

L'IA exploratoire ou freestyle est désactivée par défaut. Elle peut aider à comprendre ou signaler, mais ne transforme pas automatiquement. Elle constitue une solution de dernier recours.

---

## 5. Zones protégées

Certaines zones doivent être protégées contre les transformations ordinaires : poésie, citations anciennes, code informatique, transcriptions linguistiques, tableaux, bibliographie, notes, légendes, formules.

Une zone protégée peut empêcher une promotion en titre, une correction typographique agressive, une suggestion stylistique inadéquate ou une normalisation qui détruirait un usage savant.

Important : une zone protégée est un veto ou un signal de prudence. Elle ne remplace pas la sémantique canonique du pivot.

Exemple :

```text
protected_zone = poetry
```

ne suffit pas à garantir un export XML en `<lg>/<l>`. Le bloc doit être canonicalisé comme citation en vers :

```text
quote_kind = poetry
lineation = verse
```

---

## 6. Rôle des sorties

- `JSON` : forme stable du pivot, contrôle, debug, fixtures, traçabilité, tests.
- `DOCX` : relecture humaine avec styles visibles, corrections localisées et annotations.
- `XML‑TEI Métopes` : cible de production éditoriale.
- `LaTeX` : projection typographique future ou intermédiaire, à rattacher au pivot.
- `HTML/PDF` : visualisation, contrôle et publication de travail.

Important :

```text
styles Word Métopes != structure TEI Métopes
rendu visuel correct != pivot correct
```

---

## 7. Configuration IA

L'IA reste optionnelle. L'absence de clé IA ne doit pas empêcher le fonctionnement des modules déterministes et heuristiques.

Variables possibles :

- `PURH_AI_PROVIDER`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_BASE_URL`
- `GROQ_TIMEOUT_SECONDS`
- `GROQ_MAX_BLOCKS`

---

## 8. Lancement rapide

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Tests :

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 9. Risques connus

- pivot JSON encore insuffisamment contractualisé ;
- usage trop large de `attributes` pour des informations hétérogènes ;
- absence ou insuffisance de tests de round‑trip JSON ;
- confusion entre zone protégée et sémantique canonique ;
- gestion fine des espaces insécables et fines insécables ;
- détection des citations longues ;
- confusion entre faux titre et vers ;
- blocs Word accidentellement transformés en listes ;
- tableaux et objets complexes ;
- transcriptions linguistiques ;
- code informatique ;
- notes de bas de page et liaison appel/contenu ;
- export DOCX techniquement fragile.

---

## 10. Documentation complémentaire

- [Architecture](ARCHITECTURE.md)
- [Spécifications](SPECS.md)
- [Modèle de données](DATA_MODEL.md)
- [Contrat du pivot Python‑JSON](docs/PIVOT_JSON_CONTRACT.md)
- [Contrat des exporteurs](docs/EXPORTERS_CONTRACT.md)
- [Modèle de décision éditoriale](docs/EDITORIAL_DECISION_MODEL.md)
- [Pipeline éditorial](docs/EDITORIAL_PIPELINE.md)
- [Politique IA](AI_STYLE_POLICY_V1.md)
- [Stratégie de test](TEST_STRATEGY.md)
- [Fixtures](FIXTURES.md)
- [Mapping Métopes](METOPES_MAPPING.md)
- [Audit documentaire pivot](docs/DOCS_AUDIT_PIVOT.md)
