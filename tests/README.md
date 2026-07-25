# Tests

Les tests sont organisés en :
- `unit/` pour la logique isolée, fondée sur des fixtures synthétiques ;
- `integration/` pour les enchaînements de modules sur des DOCX synthétiques ou
  librement publiables ;
- `private_integration/` pour les tests sur corpus éditorial réel, exécutés seulement
  si `PURH_PRIVATE_CORPUS_DIR` est défini (voir `tests/private_integration/README.md`
  et `docs/CORPUS_ET_FIXTURES.md`) — ignorés avec une raison explicite sinon, jamais en
  échec faute de corpus privé ;
- `fixtures/` pour des cas minimaux temporaires dédiés à la V1.

Suite publique (toujours disponible, exécutée en CI) :

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Suite privée (nécessite le corpus privé local) :

```bash
python -m unittest discover -s tests/private_integration -p "test_*.py"
```
