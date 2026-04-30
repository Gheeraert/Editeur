# Pipeline Editorial PURH

## 1. Finalite

Le projet prepare des manuscrits auteur pour la production PURH.
Le pivot est le modele Python interne (`Document`, blocs, inlines, notes, diagnostics, transformations).

## 2. Pipeline cible

```text
DOCX auteur
  -> import riche
  -> modele Python interne structure
  -> corrections / structuration editoriale
  -> sorties:
       1) JSON (controle, debug, tracabilite, tests)
       2) DOCX (relecture humaine)
       3) XML-TEI Metopes (production principale)
```

## 3. Niveaux de decision editoriale

### 3.1 Vetos structurels (prioritaires)

Role: bloquer une transformation meme si un score est eleve.

Exemples:
- reference de passage (`VI, I, 52`, `VIII, Pr., 18`)
- legende/reference (`page 305`, `p. 390`, `accolade`, `face a`, `souligne`)
- liste (`1. ...`, puces)
- bibliographie probable
- code/balise technique
- heading explicite (selon contexte)

Statut:
- Existant: oui (structure et scoring actuel)
- Futur: extension progressive selon corpus

### 3.2 Deterministe sur

Role: transformation locale automatique quand la regle est sure.

Exemples:
- `etc...` -> `etc.`
- `1ere`/`1ere` variantes -> `1re` (selon regle en place)
- espaces typographiques avec garde-fous
- siecles styles quand contexte juge sur

Statut:
- Existant: oui (plusieurs regles orthotypo)
- Futur: durcissement par tests de garde-fous

### 3.3 Heuristique scoree

Role: arbitrer quand plusieurs indices sont necessaires.

Exemples:
- titraille
- candidats citations poetiques
- certains cas de structuration citation longue

Sortie attendue:
- `score`
- `decision` (`transform` / `diagnostic` / `ignore`)
- `evidence`
- `veto_reasons`
- `ai_candidate`

Statut:
- Existant: oui (titraille + candidats poesie)
- Futur: calibration progressive des seuils

### 3.4 IA locale (zone grise)

Role: assistance sur zones grises uniquement, jamais sur tout le document.

Contraintes:
- reponse structuree
- pas d'override des vetos (etat actuel)
- pas de correction silencieuse globale
- appel limite aux candidats heuristiques `ai_candidate=true`
- aucun appel si `veto_reasons` non vide
- aucun appel si `enable_ai=false`
- arbitrage de classification locale uniquement (pas de reecriture du texte)

Statut:
- Existant: partiel (cadre de prudence present)
- Futur: branchement explicite sur segments `ai_candidate`

### 3.5 IA exploratoire future

Role: suggestions plus ouvertes, controlees, desactivees par defaut.

Contraintes cibles:
- niveau de liberte parametrique
- suggestions uniquement, jamais corrections silencieuses

Statut:
- Existant: non
- Futur: oui (hors perimetre actuel)

## 4. Roles des sorties

- JSON: derive du pivot, utile pour debug/tests/tracabilite.
- DOCX: sortie de relecture humaine.
- XML-TEI Metopes: sortie de production principale.

## 5. Point d'attention Metopes

Les styles Word Metopes ne remplacent pas la structure TEI Metopes.
Le mapping evolue d'une logique "style Word" vers une logique "role editorial structurable".

## 6. Principes de prudence

- correction locale et motivee
- pas de reecriture massive
- en cas de doute: diagnostic plutot qu'automatisation
- IA d'assistance sous controle humain
