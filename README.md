# PURH Editorial Studio

Chaîne modulaire de préparation éditoriale pour les Presses universitaires de Rouen et du Havre (PURH).

## Philosophie actuelle (recentrage)

Le projet n'est plus pensé comme une simple chaîne "DOCX auteur -> DOCX final".

Pipeline cible:

```text
DOCX auteur
  -> import riche
  -> modèle Python interne structuré
  -> normalisations/suggestions/structuration
  -> sorties multiples:
       1) JSON (contrôle, debug, traçabilité, tests)
       2) DOCX (relecture humaine)
       3) XML-TEI Métopes (sortie principale de production)
```

Le pivot réel est le modèle Python interne (`Document`, `Block`, `InlineSpan`, `Note`, `Diagnostic`, `Transformation`, `ProcessingReport`).

## Rôle des sorties

- `JSON`: sérialisation du pivot interne, utile pour debug, tests, traçabilité et échanges techniques.
- `DOCX`: sortie de relecture humaine, avec styles visibles et corrections localisées.
- `XML-TEI Métopes`: cible de production éditoriale.

Important: styles Word Métopes et structure TEI Métopes ne sont pas équivalents. Les styles Word servent la relecture; la TEI porte la structure documentaire de production.

## Principes de prudence

- corrections localisées et motivées;
- pas de réécriture massive;
- en cas de doute: produire un diagnostic plutot qu'une transformation automatique;
- IA optionnelle: elle suggère et assiste, sans imposer silencieusement.

## Lancement rapide

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Configuration IA (Groq)

1. Copier `.env.example` vers `.env`.
2. Renseigner `GROQ_API_KEY`.

Variables:
- `PURH_AI_PROVIDER` (défaut: `groq`)
- `GROQ_API_KEY`
- `GROQ_MODEL` (défaut: `llama-3.3-70b-versatile`)
- `GROQ_BASE_URL` (défaut: `https://api.groq.com/openai/v1`)
- `GROQ_TIMEOUT_SECONDS`
- `GROQ_MAX_BLOCKS`

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Risques connus

- gestion des espaces insécables (NBSP/NNBSP) et de l'encodage;
- détection des citations longues (heuristiques à fiabiliser);
- gestion des notes de bas de page (liaison appel/contenu à stabiliser);
- export DOCX techniquement fragile (post-traitements XML/ZIP);
- documentation historique parfois trop centrée sur le DOCX.

## Documentation complémentaire

- [Architecture](ARCHITECTURE.md)
- [Data Model](DATA_MODEL.md)
- [Pipeline Editorial](docs/EDITORIAL_PIPELINE.md)
