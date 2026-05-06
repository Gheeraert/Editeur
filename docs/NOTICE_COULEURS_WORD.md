# Notice d'utilisation — Code couleur des surlignements dans le document Word

## Présentation générale

Lorsque l'outil de préparation éditoriale traite un manuscrit, il produit un document Word annoté dans lequel les passages modifiés ou à vérifier sont **surlignés en couleur**. Chaque couleur correspond à un type d'intervention précis et indique le niveau d'attention requis de la part de l'éditrice ou de l'éditeur.

Ce document est destiné à la relecture humaine : il n'est **pas** le document de production. Son rôle est de rendre visibles toutes les décisions prises par la chaîne de traitement, afin qu'un regard éditorial puisse les valider, les corriger ou les signaler.

---

## Tableau de référence rapide

| Couleur | Type d'intervention | Appliqué automatiquement ? | Action requise |
|---|---|---|---|
| Jaune | Correction orthotypographique | Oui | Vérification recommandée |
| Vert vif | Correction dans une note de bas de page | Oui | Vérification recommandée |
| Turquoise | Correction bibliographique | Oui | Vérification recommandée |
| Rose | Suggestion de l'IA (correction locale) | Non (suggestion) | Validation nécessaire |
| Violet | Suggestion de l'IA (restructuration) | Non (suggestion) | Validation nécessaire |
| Jaune foncé | Structure détectée par heuristique | Non (détection exploratoire) | Décision manuelle requise |
| Bleu-vert | Structure appliquée automatiquement | Oui | Vérification recommandée |
| **Rouge** | **Cas suspect non résolu** | **Non** | **Intervention obligatoire** |

---

## Détail des couleurs

### Jaune — Corrections orthotypographiques

Le texte surligné en **jaune** a fait l'objet d'une correction typographique ou orthographique déterministe, appliquée automatiquement selon les normes en vigueur aux PURH.

Exemples d'interventions :
- guillemets droits transformés en guillemets français (« »)
- espaces insécables avant les signes doubles (: ; ! ?)
- siècles en chiffres romains normalisés (xviie siècle)
- abréviations d'ordinaux (1er, 2e, etc.)
- tirets et tirets cadratins

Ces corrections sont fiables dans la grande majorité des cas. Une lecture rapide suffit pour repérer les cas atypiques (citations, translittérations, usage intentionnel de graphies non standard).

---

### Vert vif — Corrections dans les notes de bas de page

Le texte surligné en **vert vif** est situé dans une note de bas de page et a été corrigé automatiquement.

Exemples d'interventions :
- suppression d'espaces superflues en début ou fin de note
- ajout d'un point final manquant
- normalisation des abréviations latines (*ibid.*, *op. cit.*, *loc. cit.*, *cf.*)

Vérifier que la correction n'a pas altéré un usage volontaire (note en langue étrangère, citation non normalisée, etc.).

---

### Turquoise — Corrections bibliographiques

Le texte surligné en **turquoise** appartient à une entrée bibliographique et a été corrigé automatiquement.

Exemples d'interventions :
- point final ajouté en fin de référence
- espace insécable ajoutée dans les indications de pagination (p. 12, pp. 45-67, n° 3, fig. 2)

Ces corrections sont ciblées et localisées. Un contrôle rapide permet de s'assurer qu'elles s'appliquent bien à une bibliographie et non à un autre type de paragraphe.

---

### Rose — Suggestions de l'IA (corrections locales)

Le texte surligné en **rose** est une suggestion formulée par le module d'intelligence artificielle. Il s'agit de corrections stylistiques légères portant sur un passage court (généralement 2 à 12 mots), conformément aux règles éditoriales des PURH.

Ces suggestions **ne sont pas appliquées automatiquement** : elles apparaissent dans le document pour que l'éditrice ou l'éditeur puisse les évaluer et décider de les retenir ou de les écarter.

Attention particulière : l'IA peut se tromper sur le registre, le style propre de l'auteur ou les usages savants légitimes. Son intervention doit toujours être validée par un regard humain.

---

### Violet — Suggestions de l'IA (restructuration)

Le texte surligné en **violet** correspond à une suggestion de restructuration proposée par l'IA après arbitrage entre plusieurs interprétations possibles.

Exemples de cas traités :
- fusion de courts paragraphes susceptibles de constituer un titre
- détection de séquences poétiques
- regroupement de blocs de nature ambiguë

Ces suggestions **ne sont pas appliquées automatiquement**. Elles signalent une zone où la structure du document mérite une décision éditoriale explicite.

---

### Jaune foncé — Structure détectée en mode exploratoire

Le texte surligné en **jaune foncé** a été identifié comme une structure probable (titre, citation, poésie, liste) par le module d'analyse heuristique, mais **en mode exploratoire** : la détection n'est pas assez certaine pour être appliquée automatiquement.

Ce surlignement signale une zone grise : la chaîne a détecté un candidat éditorial, mais s'est abstenue de décider. Une décision manuelle est attendue.

Questions à se poser face à un passage en jaune foncé :
- S'agit-il bien d'un titre ? D'une citation ? D'une liste ?
- Le style Word d'origine confirme-t-il ou infirme-t-il la détection ?
- Le contexte éditorial de l'ouvrage permet-il de trancher ?

---

### Bleu-vert — Structure appliquée automatiquement

Le texte surligné en **bleu-vert** a fait l'objet d'une transformation structurelle appliquée automatiquement, parce que le niveau de confiance de la détection était suffisant.

Exemples d'interventions :
- bloc reconnu comme titre et stylé en conséquence
- séquence poétique identifiée avec certitude et balisée
- citation longue reconnue et mise en forme

Une vérification rapide reste utile pour s'assurer que la décision automatique est éditorialmente correcte dans le contexte particulier de l'ouvrage.

---

### Rouge — Cas suspect, intervention obligatoire

Le texte surligné en **rouge** signale un cas que la chaîne de traitement n'a pas pu résoudre. Le passage est ambigu, contradictoire ou insuffisamment caractérisé pour qu'une décision automatique soit prise.

**Ce surlignement exige une intervention manuelle.** Il ne disparaîtra pas sans une décision explicite de l'éditrice ou de l'éditeur.

Causes fréquentes :
- bloc très court pouvant être un titre, un vers, un item de liste ou un fragment isolé
- conflit entre plusieurs détections incompatibles
- cas atypique non couvert par les règles existantes

Face à un passage en rouge : examiner le contexte immédiat, consulter le manuscrit d'origine si nécessaire, et prendre une décision éditoriale explicite.

---

## Workflow de relecture recommandé

1. **Commencer par le rouge.** Repérer et traiter tous les passages surlignés en rouge avant tout autre chose : ce sont les seuls qui bloquent la chaîne de production.

2. **Examiner le violet et le jaune foncé.** Ces passages requièrent une décision de structure. Un choix mal posé à ce stade peut affecter la cohérence de tout le chapitre ou de tout l'ouvrage.

3. **Valider le rose.** Lire les suggestions de l'IA et décider, passage par passage, si elles sont pertinentes. En cas de doute, conserver le texte de l'auteur.

4. **Parcourir le bleu-vert.** Vérifier que les structures appliquées automatiquement sont correctes.

5. **Contrôler le jaune, le vert et le turquoise.** Ces corrections déterministes sont généralement fiables, mais un œil rapide permet de repérer les exceptions (citations non normées, usages savants spécifiques, langues étrangères).

---

## Remarques

- La **couleur disparaît** si le texte est modifié manuellement dans Word : c'est normal. La couleur est un marqueur d'annotation, non un attribut permanent du style.
- Un passage **non surligné** n'a pas été modifié par la chaîne. Il est transmis tel quel depuis le manuscrit de l'auteur.
- Ce document Word annoté **n'est pas la version finale** : il sert à la relecture. L'export de production vers XML-TEI Métopes se fait à partir du modèle pivot interne, indépendamment de ce fichier.
