# AI Style Policy (PURH)

## 1. Separation des roles IA

- IA structurelle locale: arbitre des zones grises structurelles (heading/poesie) deja detectees.
- IA editoriale: corrections ciblees du texte (module distinct).
- IA exploratoire: mode futur, non implemente dans cette passe.

## 2. Modes de decision

- `deterministic`: sans IA.
- `heuristic`: heuristiques scorees sans IA.
- `heuristic_ai_local`: heuristiques + arbitrage IA local uniquement.
- `ai_exploratory`: reserve; fallback prudent sans activation automatique.

## 3. Garde-fous obligatoires

- Un veto structurel bloque toute tentative IA locale.
- Aucun appel IA locale si `ai_candidate=false`.
- Aucun appel IA locale si le mode/option structure IA est desactive.
- L'IA locale ne reecrit jamais le texte source.
- L'IA locale repond en JSON strict et peut seulement enrichir le diagnostic.

## 4. Agressivite IA locale

- `conservative`: seuil de confiance plus haut, plafond d'appels reduit.
- `balanced`: seuil par defaut.
- `aggressive`: seuil plus bas pour diagnostic enrichi uniquement.

Dans tous les cas:
- pas d'override des vetos,
- pas d'IA free style.

## 5. Cle API en configuration locale

Le champ `ai_api_key` peut etre enregistre en clair dans le JSON de configuration de session.
Ce comportement est provisoire et doit etre considere comme sensible.

