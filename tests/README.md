# Tests

Les tests sont organisés en :
- `unit/` pour la logique isolée ;
- `integration/` pour les enchaînements de modules ;
- `fixtures/` pour des cas minimaux temporaires dédiés à la V1.

Commande d'exécution :

```bash
python -m unittest discover -s tests -p "test_*.py"
```
