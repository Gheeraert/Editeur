# Manifeste documentaire — PURH Editorial Studio

## 1. Objet

Cette archive remplace ou complète la documentation du dépôt afin de préparer une refactorisation centrée sur le pivot Python‑JSON.

Le projet ne doit pas être gouverné par les sorties, mais par un modèle pivot explicite, stable, versionné et testable.

---

## 2. Fichiers à placer à la racine du dépôt

- `README.md`
- `ARCHITECTURE.md`
- `SPECS.md`
- `DATA_MODEL.md`
- `TEST_STRATEGY.md`
- `FIXTURES.md`
- `AGENTS.md`
- `METOPES_MAPPING.md`

Les autres fichiers existants peuvent rester en place s'ils ne sont pas remplacés dans cette archive.

---

## 3. Fichiers à placer dans `docs/`

- `docs/EDITORIAL_DECISION_MODEL.md`
- `docs/EDITORIAL_PIPELINE.md`
- `docs/PIVOT_JSON_CONTRACT.md`
- `docs/EXPORTERS_CONTRACT.md`
- `docs/DOCS_AUDIT_PIVOT.md`

---

## 4. Objet de la passe

Cette passe remplace la logique :

```text
on corrige les sorties une par une
```

par la logique :

```text
on stabilise le pivot, puis les sorties le représentent
```

Elle documente :

- le statut du pivot Python‑JSON ;
- la distinction faits Word / indices / décisions / canonicalisation / export ;
- le refus des patches locaux dans les exporteurs ;
- les invariants nécessaires, notamment pour les vers ;
- les tests de round‑trip JSON ;
- les tests de cohérence entre DOCX, XML et LaTeX.

---

## 5. Formule de pilotage

```text
Si le pivot est faux, corriger l'amont.
Si le pivot est juste, corriger seulement le renderer.
Si les sorties divergent, tester d'abord le pivot.
```
