# ARCHITECTURE (recentrage progressif)

## 1. Principes directeurs

- modularité stricte;
- logique métier hors interface;
- dataclasses Python comme représentation canonique;
- transformations traçables et explicables;
- IA optionnelle et prudente.

## 2. Pivot architectural

Le pivot réel est le modèle Python interne (`Document`, blocs, inlines, notes, diagnostics, transformations, rapports).

Le JSON n'est pas le pivot souverain: c'est une sérialisation utile pour:
- debug;
- traçabilité;
- tests;
- éventuels échanges techniques (dont IA).

## 3. Pipeline cible

```text
DOCX auteur (prioritaire) / autres formats source
  -> import riche (io)
  -> modèle interne (model)
  -> services de correction/structuration (services)
  -> sorties multiples:
       - JSON de contrôle
       - DOCX de relecture humaine
       - XML-TEI Métopes (sortie principale de production)
```

## 4. Etat actuel du code (sans rupture)

- import DOCX riche déjà en place (`io/docx_importer.py`);
- traitements de normalisation orthotypographique et note/biblio déjà amorcés, à fiabiliser par des tests ciblés;
- mapping Métopes présent mais encore orienté styles Word (`services/metopes_mapper.py`);
- export DOCX de relecture en place (`io/docx_exporter.py`);
- sérialisation JSON en place (`serialization/json_serializer.py`).

Le recentrage demande une évolution progressive, sans refonte: conserver la chaîne existante et ajouter/renforcer la sortie TEI.

## 5. Styles Word Métopes vs structure TEI Métopes

- Styles Word Métopes: convention de présentation pour relecture humaine.
- Structure TEI Métopes: structuration sémantique/éditoriale pour la production.

Conclusion: un style Word appliqué sur un paragraphe n'équivaut pas automatiquement à une balise TEI correcte.

## 6. Principes de prudence applicative

- correction locale avant tout;
- pas de réécriture massive;
- en cas d'incertitude, produire un diagnostic plutôt qu'une auto-correction;
- IA sous contrôle humain (suggestion, jamais normalisation silencieuse globale).

## 7. Risques connus

- espaces insécables et encodages;
- citations longues (heuristiques);
- notes de bas de page (appel/portée/cible);
- fragilité technique de l'export DOCX;
- ancien biais documentaire centré DOCX.
