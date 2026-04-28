# PURH Editorial Studio V1 (consolidation)

Chaine modulaire de preparation editoriale pour les Presses universitaires de Rouen et du Havre (PURH).

## Ce que cette version couvre

- ingestion modulaire (`.docx`, `.xml`, `.txt`, `.md`) ;
- modele interne en dataclasses ;
- diagnostics formels + transformations sures et tracables ;
- suggestions IA prudentes (provider effectif: **Groq**) ;
- export texte + JSON ;
- interface desktop de comparaison gauche/droite.

## Consolidation ajoutee dans cette passe

### 1) DOCX enrichi (priorite haute)

L'import DOCX preserve maintenant, en plus du texte brut:
- runs inline ;
- style de paragraphe (id + nom) ;
- styles inline:
  - italique ;
  - gras ;
  - petites capitales ;
  - indice ;
  - exposant ;
- appels de notes dans le corps ;
- contenu des notes de bas de page ;
- styles inline a l'interieur des notes.

Modele enrichi:
- `InlineStyle`
- `InlineSpan`
- `Block.inlines`
- `Block.note_refs`
- `Note.inlines`

Le pivot JSON inclut ces donnees.

### 2) UI plus editoriale (sans refonte)

L'UI Tkinter reste sobre mais ajoute:
- panneaux gauche/droite en **lecture seule explicite** ;
- rendu inline (gras/italique/petites caps/superscript/subscript/note call) ;
- surlignage des blocs modifies ;
- navigation depuis diagnostics/suggestions/transformations vers le bloc cible.

### 3) Groq plus defensif

Le provider Groq est durci:
- gestion des reponses vides ;
- gestion JSON API invalide ;
- extraction JSON depuis reponse "bruitee" ou markdown ;
- gestion payload partiel ;
- non crash global: un passage en erreur est saute, avec avertissement.

## Lancement rapide

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Configuration IA (Groq)

Le provider effectif de cette V1 est **Groq**.

1. Copier `.env.example` vers `.env`.
2. Renseigner `GROQ_API_KEY`.

Variables:
- `PURH_AI_PROVIDER` (defaut: `groq`)
- `GROQ_API_KEY`
- `GROQ_MODEL` (defaut: `llama-3.3-70b-versatile`)
- `GROQ_BASE_URL` (defaut: `https://api.groq.com/openai/v1`)
- `GROQ_TIMEOUT_SECONDS`
- `GROQ_MAX_BLOCKS`

Comportement sans cle:
- application fonctionnelle ;
- module IA desactive proprement ;
- message explicite dans les avertissements.

## CLI

```bash
python cli.py <chemin_fichier> --out-dir out --disable-ai
```

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Les tests couvrent notamment:
- import DOCX enrichi (inline + notes) ;
- serialisation JSON du modele enrichi ;
- preservation inline dans le pipeline ;
- robustesse Groq (cle absente, reponse vide, JSON invalide, payload partiel).

## Limites connues

- les styles inline sont recuperes principalement via proprietes Word des runs et styles de caractere disponibles ;
- la resolution complete de tous les heritages de style Word reste partielle ;
- la normalisation inline reste prudente (preserve la structure inline, sans strategie de diff complexe) ;
- pas encore de conversion Metopes complete a ce stade (pivot prepare pour la suite).
