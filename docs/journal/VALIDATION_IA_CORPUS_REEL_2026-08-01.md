# Validation de la couche IA sur corpus réel (étape 9)

**Date :** 2026-08-01
**Backend testé :** Ollama local, `mistral-small3.2:latest` (24B, Q4_K_M)
**Corpus :** manuscrits PURH réels (accès temporaire, jamais copiés dans ce
dépôt — voir `docs/legacy/CORPUS_ET_FIXTURES.md` pour la politique de
confidentialité). Ce document ne contient **aucun extrait de manuscrit**,
uniquement des statistiques agrégées et des constats méthodologiques.

## Méthode

116 paragraphes réels échantillonnés dans 5 manuscrits stylés PURH distincts
(4 pour le texte courant, 2 pour la bibliographie) :

- 66 paragraphes de texte courant (style « Normal » ou équivalent), longueur
  ≥ 40 caractères, interrogés sur `AI_MAIN_TEXT_RULE_IDS`.
- 50 entrées de section bibliographique/sources, interrogées sur
  `AI_BIBLIOGRAPHY_RULE_IDS`.

Pour chaque paragraphe : appel réel à `OllamaAIClient.analyze_paragraph`,
puis tentative de localisation de chaque suggestion via `locate_suggestion`
(la même fonction que celle utilisée en production).

## Résultats chiffrés

| | Texte courant | Bibliographie |
|---|---:|---:|
| Paragraphes échantillonnés | 66 | 50 |
| Suggestions brutes renvoyées par le modèle | 66 (100 %) | 50 (100 %) |
| Localisées avec succès (`locate_suggestion`) | 50 (76 %) | 26 (52 %) |
| Perdues (citation non retrouvée) | 16 (24 %) | 24 (48 %) |

Répartition par règle parmi les suggestions localisées :

- Texte courant : `ia.style.lourdeur` (44), `ia.style.repetition` (6).
  Aucune occurrence de `ia.syntaxe.construction`, `ia.syntaxe.accord`,
  `ia.morphologie.forme_douteuse`, `ia.clarte.ambiguite`.
- Bibliographie : `ia.biblio.reference_incomplete` (24),
  `ia.biblio.structure_atypique` (2).

## Constat n°1 (sévérité haute) — Taux de déclenchement de 100 %

Le modèle renvoie une suggestion pour **chacun des 116 paragraphes testés**,
sans exception, malgré une consigne de prompt explicite autorisant et
demandant un tableau vide `[]` en l'absence de remarque pertinente
(`docs/CATALOGUE_REGLES_IA.md`, `prompts.py`). Un examen qualitatif des
suggestions de texte courant montre que la justification « tournure passive
excessive » revient de façon quasi systématique, y compris sur des phrases
qui ne sont grammaticalement pas à la voix passive — signe d'un diagnostic
superficiel plutôt que d'une analyse syntaxique réelle.

**Conséquence directe :** en l'état actuel du prompt, la couche IA
produirait un commentaire sur pratiquement chaque paragraphe d'un
manuscrit, ce qui est l'inverse de l'objectif (assistance sélective sur les
cas réellement problématiques). Ce n'est pas un défaut de câblage
(`locate_suggestion` et le pipeline fonctionnent comme prévu) mais un
défaut de calibration du prompt et/ou du modèle.

**Recommandation :** ne pas activer `ia.style.*` par défaut en l'état.
Retravailler le prompt (exemples few-shot avec réponse vide, critère de
sévérité explicite plus strict) puis reproduire cette validation sur un
nouvel échantillon avant réévaluation.

## Constat n°2 (sévérité haute) — Confusion entre bibliographie publiée et sources d'archives

Les deux sections « bibliographie » échantillonnées dans le corpus réel
sont en fait des **listes de sources d'archives** (dépôt : cote
(description) — ex. fonds d'archives municipales, cotes de manuscrits,
fonds photographiques), un genre éditorial distinct d'une bibliographie
d'ouvrages publiés (auteur/titre/éditeur/année/ville). `ia.biblio.
reference_incomplete` ne fait pas cette distinction et réclame
systématiquement une ville, un éditeur et une année sur des références
d'archives qui n'en comportent légitimement pas.

Dans au moins un cas observé, le modèle a **inventé** un éditeur et une
année plausibles mais fictifs pour compléter une référence d'archive qui
n'en a pas besoin — un risque plus grave qu'un simple bruit : une
suggestion fabriquée avec assurance, pas seulement inutile.

**Recommandation :** ne pas activer `ia.biblio.*` sur une section tant
qu'aucune détection (même heuristique) ne distingue bibliographie publiée
et liste de sources d'archives — les deux genres sont fréquents dans les
manuscrits PURH réels (2 sections sur 2 échantillonnées ici sont des
sources d'archives).

## Constat n°3 (taux de perte technique) — 24 % / 48 % de suggestions non localisées

Cohérent avec l'observation faite à l'étape 6 : le modèle « corrige »
parfois légèrement l'orthographe ou la ponctuation dans une citation censée
être verbatim, faisant échouer la correspondance exacte de
`locate_suggestion`. Le taux est nettement plus élevé sur la bibliographie
(48 % contre 24 % en texte courant), probablement à cause de la densité de
ponctuation et d'abréviations propres aux références. `locate_suggestion`
se comporte comme prévu (abandon silencieux plutôt qu'annotation au mauvais
endroit) — ce taux mesure une limite du modèle, pas un bug du code.

## Constat n°4 (hors périmètre IA, sévérité haute) — Incompatibilité de nommage de styles

Découverte en préparant l'échantillon, indépendante de la couche IA :
**au moins un projet PURH stylé entier (« wagner-style ») utilise des noms
de style personnalisés** (`PURH_Titre_1`, `PURH_Titre_de_chapitre`,
`PURH_Corps_de_texte`, `PURH_Citation`...) au lieu des styles natifs Word
(« Titre 1 », « Heading 1 », « Citation intense ») que `word_document.py`
et `rules/styling.py` reconnaissent exclusivement. D'autres projets stylés
du corpus (`heraldique_styles`, `dissimuler_styles`) utilisent bien les
styles natifs Word et sont donc correctement reconnus.

Sur les manuscrits utilisant la convention `PURH_*`, plusieurs mécanismes du
moteur déterministe `reborn` ne se déclenchent probablement jamais :
`purh.style.*` (application des gabarits PURH), `structure.poetry.
heuristique` (fusion poétique, qui exige le style natif « Citation
intense »), `structure.allcaps.heading`/`structure.frontmatter.*`
(détection de titre) et le ciblage bibliographique de la couche IA
(`AI_BIBLIOGRAPHY_RULE_IDS`), tous fondés sur la détection de styles natifs
Word.

**Ce constat dépasse le périmètre de l'étape 9** (chantier IA) : il concerne
la fiabilité du moteur déterministe existant sur une partie du corpus réel.
Il mérite un audit dédié pour quantifier combien de projets PURH utilisent
chaque convention, avant de décider s'il faut étendre la détection aux noms
`PURH_*` ou migrer ces manuscrits vers les styles natifs.

## Conclusion (première passe)

La mécanique technique de la couche IA (interface, parsing tolérant,
localisation, surlignage, commentaire, ciblage par nature de paragraphe)
fonctionne comme conçu, y compris sur du contenu réel dense et hétérogène.
En revanche, **la calibration du prompt actuel n'est pas prête pour un
déploiement, même optionnel** : taux de déclenchement de 100 % et confusion
entre bibliographie et sources d'archives sont deux défauts qui produiraient
plus de bruit et de risque que d'aide pour une éditrice. Le chantier IA doit
rester en l'état « disponible mais non calibré » tant qu'un nouveau cycle de
prompt engineering n'a pas été validé par une reproduction de ce protocole.

## Addendum — Effet de 4 leviers de calibration (même jour)

Sur décision explicite : le cas des dépôts d'archives (constat n°2) est mis
de côté comme cas particulier, et « un peu de bruit est acceptable dès lors
que l'IA ne fait que surligner/commenter ». Quatre leviers ciblés ont été
implémentés puis validés sur le **même échantillon** de 66 paragraphes de
texte courant, pour une comparaison directe :

1. Garde-fou déterministe : rejette toute suggestion invoquant « passif »
   sans forme conjuguée de l'auxiliaire être dans la citation.
2. Prompt : retrait de « tournure passive excessive » de la description
   d'exemple de `ia.style.lourdeur` (source probable du biais), remplacé par
   des critères plus variés et une consigne de ne l'invoquer que si elle est
   grammaticalement réelle.
3. Prompt : barre de sévérité explicite + deux exemples few-shot (réponse
   vide justifiée, suggestion genuine sans passif).
4. Température abaissée de la valeur par défaut du modèle à 0,2.

| | Avant | Après |
|---|---:|---:|
| Suggestions brutes | 66/66 (100 %) | 62/66 (94 %) |
| Localisées avec succès | 50 (76 %) | 49 (79 %) |
| Mentions de « passif » parmi les suggestions retenues | quasi systématique | 2 / 49 |

**Résultat :** le problème précis signalé (diagnostic de voix passive
erroné, y compris sur des phrases grammaticalement actives) est résolu de
façon nette et mesurable — la phrase « qui régna de 1758 à 1769 », prise à
tort pour du passif dans la première passe, reçoit désormais une critique
différente et exacte (accumulation de parenthèses). Les catégories se
diversifient aussi (`ia.syntaxe.construction`, `ia.clarte.ambiguite`
apparaissent, alors que la première passe ne produisait quasiment que
`ia.style.lourdeur`).

**Limite persistante :** le taux de déclenchement global n'a presque pas
bougé (100 % → 94 %). Le garde-fou et le prompt corrigent la *justification*
donnée, pas la *fréquence* à laquelle le modèle trouve « quelque chose » à
signaler. Réduire ce volume plus franchement demanderait des leviers non
implémentés dans cette passe (score de confiance/sévérité avec seuil, second
passage de vérification critique, ou changement de modèle) — à envisager si
94 % reste jugé trop élevé à l'usage.

## Addendum 2 — Curseur de sensibilité (score de sévérité) : biais de tendance centrale du modèle

Suite à l'ajout du score de sévérité (1-5) et du curseur associé (voir le
commit correspondant), reproduction du protocole sur le même échantillon de
66 paragraphes de texte courant, en deux passes avec des barèmes de prompt
différents :

| | Barème simple | Barème détaillé (ancres par niveau + exemple à 4) |
|---|---:|---:|
| Suggestions brutes | 60/66 (91 %) | 64/66 (97 %) |
| Sévérité 2 | 31 % | 25 % |
| Sévérité 3 | 69 % | 75 % |
| Sévérité 1, 4 ou 5 | 0 % | 0 % |

**Constat :** sur les deux passes, Mistral Small 3.2 n'utilise jamais les
sévérités 1, 4 ou 5, malgré un barème très explicite et un exemple few-shot
noté 4 pour ancrer le haut de l'échelle. Le raffinement du prompt n'a
quasiment rien changé (le taux brut a même légèrement augmenté). C'est un
signe fort de biais de tendance centrale — un comportement documenté chez de
nombreux LLM face à une échelle de notation, indépendant de la formulation
du prompt — plutôt qu'un problème de consigne à corriger par une troisième
itération.

**Conséquence pour le curseur de sensibilité :** avec ce modèle, seules les
positions 1 à 3 du curseur ont un effet réel sur le texte courant ; les
positions 4 et 5 (« Discrète ») réduisent l'assistance au silence total pour
`ia.style.*`, plutôt qu'à une sélectivité fine sur les cas les plus graves.
Le mécanisme de filtrage lui-même reste correct et se comporte exactement
comme conçu (vérifié par test d'intégration réel) : c'est la calibration du
modèle qui limite la plage utile, pas le code. Gemini et Groq n'ont pas été
testés sur ce point et pourraient se comporter différemment — à vérifier
avant de conclure que ce biais est universel plutôt que spécifique à ce
modèle local.
