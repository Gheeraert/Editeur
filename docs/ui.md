# UI V1 consolidee

## Objectif

Comparer visuellement:
- source a gauche ;
- texte style/normalise a droite.

## Ameliorations de cette passe

- panneaux source/styled explicitement en lecture seule ;
- rendu inline (gras, italique, petites caps, indice, exposant, appels de note) ;
- surlignage des blocs modifies ;
- navigation vers bloc cible depuis:
  - diagnostics ;
  - suggestions IA ;
  - transformations.

## Fonctions disponibles

- ouvrir un fichier (`docx`, `xml`, `txt`, `md`) ;
- charger un document depuis `sources/` ;
- limiter la taille d'extrait ;
- activer/desactiver le module IA Groq ;
- relancer le pipeline ;
- consulter diagnostics/suggestions/transformations/avertissements ;
- exporter texte style, rapport JSON, payload pivot JSON.

## Notes d'usage

- pas d'edition directe du texte dans l'UI ;
- la logique metier reste dans `services/` + `pipeline/` ;
- la source est conservee distinctement.
