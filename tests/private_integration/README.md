# Tests privés sur corpus réel

Ces tests ne s'exécutent que si la variable d'environnement
`PURH_PRIVATE_CORPUS_DIR` pointe vers un corpus privé local installé. Voir
`docs/CORPUS_ET_FIXTURES.md` pour la politique complète et
`src/purh_editorial/config/private_corpus.py` pour la résolution du chemin.

## Pourquoi une suite séparée

Le corpus éditorial privé (manuscrits réels, versions corrigées par les éditrices) n'est
jamais suivi par Git dans ce dépôt public. Ces tests vérifient malgré tout, sur machine
locale disposant du corpus, ce que les tests publics synthétiques ne peuvent pas
couvrir : idempotence et conservation documentaire sur de vrais manuscrits volumineux,
comparaison avec de vraies copies corrigées.

## Exécution

```bash
export PURH_PRIVATE_CORPUS_DIR="C:/Editeur-private"   # ou set sous PowerShell/cmd
python -m unittest discover -s tests/private_integration -p "test_*.py"
```

Sans cette variable (cas normal en CI publique), toute la suite est automatiquement
ignorée (`skip`), jamais en échec.

## Structure attendue du corpus privé

```text
<PURH_PRIVATE_CORPUS_DIR>/
└── sources/
    ├── manuscripts_raw/       # au moins 2 fichiers .docx, découverts dynamiquement
    └── io_samples/
        ├── pairs.json         # optionnel : couples {"raw", "reference", "check"}
        └── ...                # fichiers référencés par pairs.json
```

Aucun nom de fichier réel, titre ou auteur n'apparaît dans le code de test : tout est
découvert dynamiquement à partir de ce qui est présent localement.
