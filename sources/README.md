# Sources

Ce dossier accueille localement le corpus éditorial privé (manuscrits réels, documents
internes PURH, sources de référence) — **jamais suivi par Git dans ce dépôt public.**

Voir `docs/legacy/CORPUS_ET_FIXTURES.md` pour la politique telle que définie avec la
voie legacy. Le chargeur automatique (`PURH_PRIVATE_CORPUS_DIR`,
`src/purh_editorial/config/private_corpus.py`) a été supprimé avec le reste de la voie
legacy ; ce dossier reste réservé au corpus privé si ce dispositif est reconstruit pour
`reborn`.

## Installer le corpus privé localement

Le corpus privé n'est pas distribué avec ce dépôt. Pour l'installer, obtenez-le
séparément (transmission directe) et placez-le où vous le souhaitez, puis :

```bash
export PURH_PRIVATE_CORPUS_DIR="/chemin/vers/le/corpus/prive"
```

Le pipeline et les tests publics fonctionnent entièrement sans cette variable ; seuls
les tests de `tests/private_integration/` l'utilisent, et s'ignorent proprement en son
absence.

## Ce fichier est le seul contenu de sources/ suivi par Git

Tout le reste de ce dossier (sous-dossiers, fichiers binaires) est ignoré par
`.gitignore` — voir la règle `sources/** / !sources/README.md` à la racine du dépôt.
