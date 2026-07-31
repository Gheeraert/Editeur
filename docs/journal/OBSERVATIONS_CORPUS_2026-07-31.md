# Observations sur six nouveaux manuscrits privés — synthèse publique

Rapport diagnostique. Complète `docs/journal/ANALYSE_CORPUS_HP2.md` avec six manuscrits
supplémentaires. Une seule règle a été ajoutée au code à la suite de cette analyse
(`purh.date.jour_mois`, voir dernière section) ; les autres observations sont documentées
ici sans modification de code, par prudence — chacune présente un risque de faux positif
non résolu.

**Confidentialité** : les manuscrits sont désignés par des identifiants génériques
(`private_corpus_e` à `private_corpus_j`), conformément au principe déjà appliqué dans
`docs/journal/PHASE1_FIABILITE_PIPELINE.md` (voir aussi `docs/legacy/CORPUS_ET_FIXTURES.md`
pour le dispositif d'origine). Aucun titre, auteur, nom d'éditeur ni extrait de plus de
quelques mots n'apparaît ici.

## Méthode

Pour chacun des six manuscrits (`sources/manuscripts_raw/`, avec pendant corrigé dans
`sources/manuscripts_styled/`) : extraction paragraphe par paragraphe du brut et du
corrigé, appariement par clé lexicale (les 40 premiers caractères alphanumériques),
application des règles de texte actuellement actives au brut, comparaison au corrigé réel.

**Limite assumée** : cette méthode produit du bruit sur les textes fortement réécrits sur
le fond (plusieurs de ces six manuscrits relèvent des sciences humaines et de la
littérature, davantage réécrits que le corpus académique de référence déjà analysé) —
certains appariements associent deux paragraphes qui divergent par une réécriture de fond
plutôt que par un écart typographique. Les observations ci-dessous ont été vérifiées
individuellement sur les paires concernées, pas seulement comptées.

Un septième manuscrit a été reçu en deux versions du corrigé : la première (un export
depuis une mise en page) s'est révélée avoir perdu la totalité de ses espaces insécables
au passage, contrairement à la seconde (fichiers Word natifs, un par chapitre) — écartée
des comptages, cette première version illustre un risque méthodologique à garder en tête
pour toute analyse future basée sur un export de mise en page plutôt qu'un document de
travail éditorial.

## Confirmation : l'espace insécable normale, pas la fine

Résultat déjà documenté ailleurs (voir historique des commits), reconfirmé ici sur ces six
manuscrits indépendamment des deux premiers qui avaient servi à l'établir : sur plusieurs
dizaines de milliers d'espaces insécables réelles comptées (bruts et corrigés confondus),
une fraction négligeable (inférieure à 0,1 %, sans motif récurrent identifiable) est la
fine insécable. Aucune anomalie nouvelle.

## Observation 1 — titres de section tout capitales → casse phrase (reconfirmée)

Motif déjà repéré dans `docs/journal/ANALYSE_CORPUS_HP2.md` (catégorie 2d) : un titre de
section en capitales dans le brut est systématiquement ramené à la casse phrase par les
éditrices (`structure.allcaps.heading`, toujours dans les règles de structure non
câblées — voir `runner.py`, `NOT_YET_IMPLEMENTED_RULE_IDS`). Une occurrence supplémentaire
observée sur `private_corpus_f`, indépendante du corpus qui avait motivé la fiche
d'origine. Pas de changement de recommandation : cette règle reste hors périmètre tant que
la famille structure n'est pas retravaillée dans son ensemble (repose sur des heuristiques
de style que `docs/REBORN_ARCHITECTURE.md` §7 exclut par construction).

## Observation 2 — nombre attaché à un nom propre au-delà des dates

En plus du motif jour + mois (implémenté, voir dernière section), deux occurrences
observées (`private_corpus_i`, `private_corpus_j`) d'un numéro attaché sans espace
insécable à un nom propre — un lieu ou une institution suivie d'un numéro, dans le même
esprit que `purh.numeral_dynastique` (chiffre romain après nom propre) mais avec un
chiffre arabe.

**Non implémenté, délibérément.** `purh.numeral_dynastique` reste sûr parce qu'un chiffre
romain isolé après un mot capitalisé est rare hors contexte de nom propre. Un chiffre
arabe après un mot capitalisé est beaucoup plus fréquent en début de phrase (« Le 24…»,
« Un 15… ») où le mot capitalisé n'est qu'un article ou un pronom de début de phrase, pas
un nom propre — une règle positionnelle sans distinction produirait des faux positifs
massifs, du même ordre que la virgule d'incise déjà écartée en catégorie 3 de
`ANALYSE_CORPUS_HP2.md`. Seulement deux occurrences observées, pas assez pour caractériser
un motif fiable de reconnaissance de nom propre. À reprendre seulement si un vrai signal de
reconnaissance d'entité nommée (majuscule répétée sur plusieurs mots consécutifs, position
en tête de paragraphe type page de titre, etc.) peut border la règle sans ambiguïté.

## Observation 3 — risque de régression sur citation en langue étrangère

Un manuscrit (`private_corpus_i`) contient des épigraphes en langue étrangère. La règle
`purh.espaces.avant_ponct_forte` (espace insécable avant `: ; ? !`) ne sait pas qu'un
passage cité est dans une autre langue et lui applique l'espacement français avant un
point-virgule — un cas où l'application de la règle **dégraderait** un texte déjà correct
plutôt que de corriger un texte fautif, à la différence de toutes les autres observations
de ce document.

**Non traité.** Aucune détection de langue n'existe dans `reborn`, et en ajouter une
serait disproportionné pour quelques épigraphes isolées sur un seul manuscrit sur sept.
À noter comme limite connue. Si des citations en langue étrangère devenaient fréquentes
dans un futur manuscrit, une zone protégée simple (bloc de citation attribué, plutôt
qu'une détection de langue) serait la piste la plus sûre à explorer en premier.

## Ce qui a été implémenté à la suite de cette analyse

`purh.date.jour_mois` : espace insécable entre un quantième (1 à 31) et le nom de mois qui
le suit directement, sur liste fermée des douze mois. Motif observé de façon répétée et
sans ambiguïté sur trois des six manuscrits (dates historiques datées). Contrairement à
l'observation 2, le nom de mois donne un contexte fermé et sans ambiguïté qui élimine le
risque de faux positif en début de phrase — le mot suivant le nombre est toujours l'un des
douze mois, jamais un mot de phrase ordinaire. Validé sans faux positif détecté sur
l'ensemble des six manuscrits (voir tests, `purh.date.jour_mois`).

## Synthèse

- **0 défaut** dans les règles existantes détecté sur ce lot (contrairement à Phase 1 sur
  le premier corpus).
- **1 règle implémentée** (`purh.date.jour_mois`) grâce à un motif à risque de faux positif
  nul (liste fermée de mois).
- **1 motif reconfirmé mais toujours hors périmètre** (titres tout capitales — famille
  structure entière à retravailler, pas un correctif isolé).
- **2 observations documentées sans code** : généralisation du numéral après nom propre
  aux chiffres arabes (risque de faux positif de début de phrase, échantillon insuffisant)
  et risque de régression sur citation en langue étrangère (cas marginal, pas de détection
  de langue disponible).

Aucune fixture n'a été modifiée pour produire ce document au-delà des tests couvrant
`purh.date.jour_mois`.
