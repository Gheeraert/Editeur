# RULES_CATALOG (SHS, version operationnelle)

Ce catalogue organise les regles selon un mecanisme de decision editorial a 5 niveaux.

## Legende automatisation

- `A1` auto-correction sure
- `A2` suggestion localisee
- `A3` diagnostic seulement
- `A4` hors perimetre initial

## Niveaux de decision (transversal)

### 1) Vetos structurels (prioritaires)

Un veto bloque la transformation, meme si le score est eleve.

Vetos types:
- `passage_reference`
- `caption_or_reference`
- `list_like`
- `bibliography_like`
- `technical_markup`
- `poetry_line_candidate`
- `heading_explicit` (selon contexte)

Etat:
- Existant: oui (structure/titraille/poesie)
- Futur: enrichissement des cas limites

### 2) Deterministe sur

Regles locales et testables, appliquees automatiquement quand le contexte est stable.

Exemples:
- `R-AB-001` (`etc...` -> `etc.`)
- `R-SO-002` ordinaux simples (`1re`, `5e`)
- `R-SP-002`, `R-SP-003` (espaces locaux)
- siecles styles quand contexte robuste

Etat:
- Existant: oui (partiel selon regles)
- Futur: extension avec garde-fous

### 3) Heuristique scoree

Utilisee quand plusieurs indices doivent etre combines.

Sortie attendue:
- score
- decision (`transform` / `diagnostic` / `ignore`)
- evidence
- veto_reasons
- ai_candidate

Exemples:
- `R-STRUCT-HEADING-001` (candidats heading)
- `R-CI-POETRY-001` (candidats citation poetique)

Etat:
- Existant: oui
- Futur: recalibrage seuils sur corpus reel

### 4) IA locale (zone grise)

Usage cible:
- uniquement sur segments `ai_candidate`
- sortie structuree
- pas d'override des vetos

Etat:
- Existant: cadre de prudence, pas de generalisation automatique
- Futur: branchement local par type de decision

### 5) IA exploratoire future

Usage cible:
- desactivee par defaut
- suggestions uniquement
- niveau de liberte parametrique

Etat:
- Existant: non
- Futur: oui

## Extraits de regles prioritaires (rappel)

### Espaces et ponctuation

- `R-SP-001` espaces avant `: ; ? !` avec garde-fous (URL/heures/ratios/paths/refs)
- `R-SP-002` suppression espace avant `, .`
- `R-SP-003` reduction doubles espaces
- `R-SP-004` separateur des milliers

### Guillemets

- `R-GQ-001` conversion prudente des guillemets droits (`A2` par defaut)
- `R-GQ-004` ponctuation autour des guillemets (`A3`)

### Notes

- `R-AN-002` placement appel de note vs ponctuation (`A3`)
- `R-AN-003` espace parasite avant appel de note (`A3`)

### Structuration

- `R-TI-001` hierarchie de titres
- `R-STRUCT-HEADING-001` decision scoree heading + vetos
- `R-CI-POETRY-001` decision scoree candidats poesie + vetos

## Points explicitement futurs

- IA locale active sur zones grises (non generalisee aujourd'hui)
- IA exploratoire (desactivee par defaut)
- normalisation bibliographique exhaustive multi-modeles
