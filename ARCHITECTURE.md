# ARCHITECTURE (recentrage progressif)

## 1. Principes directeurs

- modularite stricte
- logique metier hors UI
- dataclasses Python comme pivot
- transformations tracables
- IA optionnelle et prudente

## 2. Pivot architectural

Pivot reel: modele Python interne (`Document`, blocs, inlines, notes, diagnostics, transformations, report).

JSON:
- derive du pivot
- utile pour debug/tests/tracabilite
- non souverain

## 3. Pipeline cible

```text
DOCX auteur
  -> import riche
  -> modele interne
  -> services de correction/structuration
  -> sorties:
       - JSON de controle
       - DOCX de relecture
       - XML-TEI Metopes (production)
```

## 4. Niveaux de decision editoriale

1. Vetos structurels (prioritaires): bloquent la transformation.
2. Deterministe sur: auto-corrections locales robustes.
3. Heuristique scoree: score + decision + evidence + veto_reasons + ai_candidate.
4. IA locale (zone grise): cible future proche, sans override des vetos.
5. IA exploratoire future: desactivee par defaut, suggestions uniquement.

## 5. Existant vs futur

- Existant:
  - vetos et heuristiques scorees en structure (heading/poesie)
  - regles deterministes orthotypographiques
  - diagnostics structurés
- Futur:
  - activation locale explicite de l'IA sur zones grises
  - mode IA exploratoire parametre

## 6. Metopes: style Word vs structure TEI

- style Word Metopes: relecture/mise en forme
- structure TEI Metopes: semantique de production

Conclusion: style Word != structure TEI.
