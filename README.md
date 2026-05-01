# PURH Editorial Studio

Chaîne modulaire de préparation éditoriale pour les Presses universitaires de Rouen et du Havre (PURH).

## 1. Philosophie générale

Le projet n'est plus pensé comme une simple chaîne :

```text
DOCX auteur -> DOCX corrigé
```

Il vise une chaîne éditoriale complète :

```text
DOCX auteur
  -> import riche
  -> modèle Python interne structuré
  -> diagnostics / corrections / structuration
  -> sorties multiples :
       1) JSON de contrôle
       2) DOCX de relecture humaine
       3) XML-TEI Métopes de production
```

Le pivot réel est le modèle Python interne : `Document`, `Block`, `InlineSpan`, `Note`, `Diagnostic`, `Suggestion`, `Transformation`, `ProcessingReport`.

---

## 2. Problème traité

Un manuscrit auteur n'est jamais une structure éditoriale propre. Un fichier Word contient des faits matériels : styles, gras, italique, retraits, puces, notes, tableaux, citations, accidents de mise en forme.

Ces faits peuvent être utiles, mais ils peuvent aussi mentir. Un paragraphe Word stylé comme un titre peut être un vrai titre, mais aussi un vers accidentellement stylé, une ligne de poésie devenue puce, une légende, une référence ou un fragment de transcription.

Le projet doit donc distinguer :

```text
fait matériel -> indice -> candidat éditorial -> décision -> transformation
```

Cette logique est décrite dans `docs/EDITORIAL_DECISION_MODEL.md`.

---

## 3. Régimes d'action

### 3.1 Déterministe

Règles locales, explicites, testables : espaces typographiques, guillemets, appels de notes, siècles, abréviations, corrections locales sûres.

### 3.2 Heuristique scorée

Détection de structures probables, avec score, justification et vetos : titre probable, citation longue, séquence poétique, bibliographie, code, transcription linguistique.

### 3.3 IA locale encadrée

L'IA locale ne doit intervenir qu'en zone grise, sur une question fermée et courte. Elle ne décide pas souverainement et ne passe pas outre les vetos.

### 3.4 IA exploratoire

L'IA exploratoire ou freestyle est désactivée par défaut. Elle peut aider à comprendre ou signaler, mais ne transforme pas automatiquement. Elle constitue une solution de dernier recours.

---

## 4. Principe de prudence

Le système doit préférer :

```text
diagnostic plutôt que transformation douteuse
abstention plutôt que réécriture abusive
traçabilité plutôt qu'efficacité opaque
```

Toute transformation doit être localisée, motivée, journalisée, testable, réversible et validable humainement.

---

## 5. Zones protégées

Certaines zones doivent être protégées contre les transformations ordinaires : poésie, citations anciennes, code informatique, transcriptions linguistiques, tableaux, bibliographie, notes, légendes, formules.

Une zone protégée peut empêcher une promotion en titre, une correction typographique agressive, une suggestion stylistique inadéquate ou une normalisation qui détruirait un usage savant.

---

## 6. Rôle des sorties

- `JSON` : contrôle, debug, fixtures, traçabilité.
- `DOCX` : relecture humaine avec styles visibles, corrections localisées et annotations.
- `XML-TEI Métopes` : cible de production éditoriale.

Important :

```text
styles Word Métopes != structure TEI Métopes
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
- [Modèle de décision éditoriale](docs/EDITORIAL_DECISION_MODEL.md)
- [Politique IA](AI_STYLE_POLICY_V1.md)
- [Stratégie de test](TEST_STRATEGY.md)
- [Fixtures](FIXTURES.md)
- [Mapping Métopes](METOPES_MAPPING.md)
- [Pipeline éditorial](docs/EDITORIAL_PIPELINE.md)
