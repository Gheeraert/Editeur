# Corpus d'or normatif — orthotypographie

Voir `SCHEMA.md` pour le format et `docs/CORPUS_ET_FIXTURES.md` pour la politique
publique/privée complète.

**Aucun cas de ce dossier n'a été inventé ou déduit du comportement actuel du code.**
Chaque cas est validé indépendamment (voir `validation_source` dans chaque fichier).

## État actuel

Deux règles ont un cas normatif public à ce jour, toutes deux sourcées par une
prescription non ambiguë et publique du guide PURH réel (`validation_source.type:
"guide_purh"`, citation courte et factuelle, non sensible) :

- `purh_abreviations_redoublement.json`
- `purh_ordinaux.json`

Toutes les autres règles du catalogue n'ont **aucun** cas d'or public pour l'instant :
c'est un état de fait, pas une lacune à masquer. Voir
`docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md` pour le détail règle par règle, et
`docs/CORPUS_ET_FIXTURES.md` pour comment ajouter un cas `editorial_copy` ou
`human_validation` (dont les données réelles resteraient dans le corpus privé).

## Ne jamais faire

- Ajouter un cas sans un `validation_source` réel et vérifiable.
- Copier une sortie du code dans ce dossier en la faisant passer pour normative.
- Ajouter un cas `editorial_copy`/`human_validation` avec des données réelles
  publiées ici — leur place est dans `C:\Editeur-private\private_fixtures\`.
