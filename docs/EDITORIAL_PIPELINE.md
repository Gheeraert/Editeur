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

### 3.0 Modes de decision (configuration)

Le pipeline prepare quatre modes de decision:
- `deterministic`
- `heuristic`
- `heuristic_ai_local`
- `ai_exploratory` (reserve, non implemente)

Comportement actuel:
- `deterministic`: aucun appel IA; certaines heuristiques structurelles peuvent encore rester actives selon les limites actuelles du pipeline.
- `heuristic`: heuristiques scorees + diagnostics; aucun appel IA.
- `heuristic_ai_local`: heuristiques scorees + arbitrage IA structurel local sur zones grises uniquement.
- `ai_exploratory`: fallback prudent vers heuristique sans IA + warning.

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

Configuration actuelle:
- `heuristic_profile`: `conservative` / `balanced` / `exploratory`
- overrides optionnels:
  - `heading_transform_threshold`
  - `heading_diagnostic_threshold`
  - `poetry_transform_threshold`
  - `poetry_diagnostic_threshold`
- Les vetos restent prioritaires quel que soit le profil.

### 3.4 IA locale (zone grise)

Role: assistance sur zones grises uniquement, jamais sur tout le document.

Contraintes:
- reponse structuree
- pas d'override des vetos (etat actuel)
- pas de correction silencieuse globale
- appel limite aux candidats heuristiques `ai_candidate=true`
- aucun appel si `veto_reasons` non vide
- aucun appel si `enable_structure_ai=false`
- arbitrage de classification locale uniquement (pas de reecriture du texte)
- vetos prioritaires, jamais surcharges

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

## 3.6 IA editoriale vs IA locale

- IA structurelle locale: arbitre un candidat heuristique local (heading/poesie), sans modifier le texte.
- IA editoriale: corrections ciblees pouvant modifier le texte.
- Les deux families sont configurees separement.

## 3.7 Agressivite IA locale

Niveaux prepares:
- `conservative`
- `balanced`
- `aggressive`

Etat actuel:
- agit sur le seuil de confiance et le plafond local d'appels,
- ne desactive jamais les vetos,
- n'autorise aucune transformation automatique free style.

## 3.8 Securite configuration

Le JSON de configuration de session peut contenir `ai_api_key` en clair.
Attention: ce stockage est local et non chiffre dans cette passe.

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
