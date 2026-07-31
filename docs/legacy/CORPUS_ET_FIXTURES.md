# Corpus et fixtures — politique publique/privée

Ce document définit la frontière entre ce qui est public dans ce dépôt et ce qui reste
strictement local. Il remplace, pour cette question, toute mention éparse antérieure de
« corpus H&P2 » ou de manuscrits nommément identifiés dans la documentation publique.

## Les quatre catégories

### 1. Corpus éditorial privé

Documents complets réels : manuscrits d'auteur, versions corrigées par les éditrices,
épreuves, documents internes PURH (consignes aux auteurs, chartes graphiques, gabarits
Word/InDesign), sources de référence non redistribuables (lexiques sous droits, polices
commerciales).

**Ces documents ne sont jamais suivis par Git dans ce dépôt public.** Ils vivent
uniquement dans un espace privé local (voir « Installer le corpus privé » ci-dessous) et
sont désignés dans le code, les tests et la documentation par des identifiants
génériques (`private_corpus_a`, `private_corpus_b`, …), jamais par le titre, l'auteur ou
tout autre élément permettant de les identifier.

### 2. Corpus de caractérisation

Cas qui enregistrent **ce que le programme produit actuellement**. Ils répondent à la
question : *que produit le code aujourd'hui ?*

Ils ne prouvent pas qu'un comportement est éditorialement correct. Un cas de
caractérisation peut délibérément figer un comportement **connu comme discutable ou
erroné**, dans le seul but de détecter un changement non intentionnel (non-régression).
Voir `fixtures/orthotypography_characterization/README.md`.

### 3. Corpus d'or normatif

Cas dont la sortie attendue a été établie **indépendamment du code**, par l'une des voies
suivantes uniquement :
- validation explicite d'une éditrice PURH ;
- correspondance exacte avec une copie corrigée publiée ou validée ;
- prescription non ambiguë du guide typographique PURH, citée avec sa référence précise.

Ils répondent à la question : *que doit produire le programme ?*

**Aucun cas ne porte le nom de corpus d'or sans l'une de ces validations indépendantes.**
Le schéma attendu pour un cas normatif est documenté dans
`fixtures/orthotypography_gold/README.md` ; les données normatives réelles (quand elles
existent) restent dans le corpus privé local, jamais publiées ici.

### 4. Fixtures publiques synthétiques

Cas minimaux inventés uniquement pour les tests techniques : chaînes artificielles,
petits DOCX synthétiques, exemples neutres. Aucun contenu éditorial sensible, aucun
extrait d'ouvrage réel.

## Installer le corpus privé localement

Le pipeline et les tests publics fonctionnent **sans** le corpus privé. Pour l'installer
et activer les tests privés :

1. Obtenir le corpus privé (hors dépôt Git, transmission directe).
2. Définir la variable d'environnement `PURH_PRIVATE_CORPUS_DIR` pointant vers son
   dossier racine local (voir `src/purh_editorial/config/private_corpus.py`).
3. Lancer la suite de tests privés (voir `tests/private_integration/README.md`).

Sans cette variable, les tests privés sont automatiquement ignorés (`skip`), avec un
message explicite — jamais un échec.

## Ce que la documentation publique ne doit jamais contenir

- le titre complet, l'auteur ou tout identifiant d'un ouvrage du corpus privé ;
- un extrait de plus de quelques mots tiré d'un manuscrit ou d'une épreuve réelle ;
- le contenu verbatim d'un document interne PURH (consignes aux auteurs, gabarits) —
  seules des citations ponctuelles et courtes, avec référence de page, sont admises pour
  sourcer une règle ;
- un nombre suffisant de détails pour reconstituer, même partiellement, un document
  privé.

Les rapports d'analyse qui portaient sur le corpus privé (audits de phases antérieures)
ont été remplacés par des versions publiques expurgées ou déplacés intégralement dans
l'espace privé local (`C:\Editeur-private\private_reports\`). Voir le journal de la
passe d'assainissement pour le détail de ce qui a été déplacé.
