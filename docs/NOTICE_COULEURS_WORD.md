# Notice d'utilisation — Code couleur des surlignements dans le document Word

## Présentation générale

Le correcteur `reborn` (`corrector/word_document.py`) travaille sur une copie du manuscrit et surligne chaque intervention directement dans le document Word produit. Trois couleurs sont utilisées aujourd'hui — le périmètre pourra s'enrichir en même temps que de nouvelles règles seront ajoutées (cf. [`docs/REBORN_ARCHITECTURE.md`](REBORN_ARCHITECTURE.md)).

Ce document Word annoté est destiné à la relecture humaine : aucune intervention automatique n'est réputée définitive tant qu'elle n'a pas été vérifiée par l'éditrice ou l'éditeur.

---

## Tableau de référence

| Couleur | Type d'intervention | Le texte a-t-il été modifié ? | Action requise |
|---|---|---|---|
| **Jaune** | Correction ortho-typographique ou bibliographique déterministe (règle `deterministic` du catalogue) | Oui | Vérification recommandée |
| **Turquoise** | Diagnostic heuristique (règle `heuristic` du catalogue signalant un cas ambigu) | Non | Décision manuelle requise |
| **Vert clair** | Restructuration du texte (fusion des strophes/citations poétiques en un paragraphe unique) | Oui (fusion) | Vérification recommandée |

---

## Jaune — corrections appliquées automatiquement

Regroupe toutes les règles `text_transform`/`style_transform` déterministes actuellement câblées : espaces typographiques, guillemets, apostrophes, ligature « œ », siècles en petites capitales, ordinaux, civilités, abréviations, pagination et numérotation (y compris dans les entrées bibliographiques), corrections dans les notes de bas de page.

Ces corrections sont fiables dans la grande majorité des cas. Un passage rapide suffit pour repérer les cas atypiques (citations, translittérations, usages savants intentionnels).

## Turquoise — diagnostics signalés, texte inchangé

Regroupe les règles heuristiques qui détectent un cas nécessitant un jugement éditorial mais **ne modifient pas le texte** : tirets d'incise ambigus, guillemets droits, appels de note mal placés, débuts de note en minuscule, ponctuation finale ambiguë en note.

Chaque passage turquoise appelle une lecture attentive : la chaîne a repéré un cas potentiellement problématique, mais s'abstient de trancher automatiquement.

## Vert clair — restructuration du texte

Regroupe les règles de structuration qui modifient l'agencement des paragraphes : la fusion des strophes/citations poétiques (`structure.poetry.heuristique`) en un paragraphe unique. Le texte est bien modifié (fusion), d'où la nécessité d'un surlignage même si la règle reste d'inspiration heuristique.

---

## Remarques

- Un passage **non surligné** n'a pas été touché par l'outil ; il est transmis tel quel depuis le manuscrit de l'auteur.
- La famille de règles « structuration du texte » couvre pour l'instant la fusion des citations poétiques (vert clair), les titres tout en majuscules et le frontmatter (turquoise) ; les autres cas prévus par le catalogue restent à implémenter.
- La couleur disparaît si le texte est ensuite modifié manuellement dans Word : c'est normal, il s'agit d'un marqueur d'annotation, pas d'un attribut permanent du style.
