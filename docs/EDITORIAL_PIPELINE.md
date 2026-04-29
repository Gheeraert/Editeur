# Pipeline Editorial PURH

## 1. Finalite

Le projet prépare des manuscrits auteur pour la production PURH.
Le recentrage architectural conserve l'existant et clarifie la cible.

## 2. Pipeline cible

```text
DOCX auteur
  -> import riche
  -> modèle Python interne structuré
  -> corrections et structuration éditoriale
  -> sorties:
       1) JSON (contrôle/debug/traçabilité/tests)
       2) DOCX (relecture humaine)
       3) XML-TEI Métopes (production principale)
```

## 3. Roles explicites

- Pivot interne: dataclasses métier (`Document`, blocs, inlines, notes, diagnostics, transformations).
- JSON: format dérivé, pas pivot souverain.
- DOCX: support de vérification humaine, avec corrections localisées visibles.
- XML-TEI Métopes: sortie éditoriale de référence pour la production.

## 4. Point d'attention Metopes

Les styles Word Métopes sont utiles pour la relecture et la mise en forme.
Ils ne remplacent pas la structuration TEI Métopes.

Le mapping Métopes doit évoluer progressivement:
- d'une logique "assigner un style Word";
- vers une logique "identifier un rôle éditorial structurable en TEI".

## 5. Principes de prudence

- correction locale et motivée;
- pas de réécriture massive;
- en cas de doute: diagnostic explicite plutôt qu'automatisation;
- IA d'assistance seulement, sans imposition silencieuse.

## 6. Risques connus a surveiller

- espaces insécables (NBSP/NNBSP) et encodage;
- détection des citations longues;
- gestion des notes de bas de page;
- fragilité technique de certains post-traitements DOCX;
- traces de documentation historique centrée DOCX.
