# PURH Editorial Studio — correcteur ortho-typographique

Outil d'assistance à la correction éditoriale pour les Presses universitaires de Rouen et du Havre (PURH).

## 1. Ce que fait l'outil

L'outil ouvre une copie d'un manuscrit Word (`.docx`) envoyé par une autrice ou un auteur, applique les règles ortho-typographiques du catalogue PURH, **surligne chaque intervention** et enregistre un nouveau document. Le fichier original n'est jamais modifié.

```text
DOCX auteur (copie) -> détection des cas prévus par les règles -> corrections + surlignage -> nouveau DOCX
```

- **Surlignage jaune** : correction appliquée automatiquement (le texte a été modifié).
- **Surlignage turquoise** : diagnostic signalé, texte inchangé — nécessite une décision humaine.

Aucune intervention n'est silencieuse : toute règle qui modifie ou signale quelque chose laisse une trace visible dans le document de sortie, à vérifier par l'éditrice avant validation finale.

## 2. Normes appliquées

Les règles typographiques en vigueur à l'Imprimerie nationale, complétées et priorisées par les consignes propres aux PURH (en cas de conflit, les consignes PURH l'emportent). La liste normative complète — 61 règles réparties en quatre familles (ortho-typo de base, notes de bas de page, bibliographie, structuration du texte) — est documentée dans [`docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`](docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md), la source de vérité du projet.

## 3. Périmètre actuellement couvert

L'outil est en cours de construction incrémentale. À ce stade :

| Famille | Règles couvertes / catalogue |
|---|---:|
| Ortho-typographie de base | 22 / 23 |
| Notes de bas de page | 10 / 10 |
| Bibliographie | 3 / 7 |
| Structuration du texte | 3 / 21 |
| **Total** | **38 / 61** |

La bibliographie repère désormais sa section (au style de titre Word associé au titre « Bibliographie »/« Sources »...) pour y ajouter le point final manquant. Le frontmatter (résumé, mots-clés, remerciements) est signalé en diagnostic (surlignage turquoise) plutôt que reclassé automatiquement, faute de style Word cible défini par le catalogue. **La détection de titres, de poésie et de citations comme éléments de structure n'est pas prioritaire pour l'instant** : elle reposait, dans l'architecture antérieure, sur un moteur de score que la stratégie actuelle exclut, sa reconception sans score est un travail éditorial à part entière, et la priorité reste de consolider l'ortho-typo/notes/bibliographie avant de s'y attaquer. Le détail de l'écart entre le catalogue et ce qui est effectivement câblé, ainsi qu'un plan de travail pour étendre l'automatisation bibliographique, sont suivis dans [`docs/REBORN_ARCHITECTURE.md`](docs/REBORN_ARCHITECTURE.md) (sections « État réel d'implémentation » et « Faisabilité d'une automatisation bibliographique plus poussée »).

## 4. Prérequis

- Windows, avec **Microsoft Word installé** : la correction pilote Word directement via COM (`pywin32`), ce qui préserve la mise en page, les styles, les notes, les tableaux et les images du document original.
- Python 3.11+.

## 5. Lancement

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Une fenêtre s'ouvre : choisir le document source, choisir (ou laisser proposer) le document de sortie, cliquer sur « Corriger ». Le résultat affiche le nombre d'interventions par règle.

### Assistance IA (optionnelle)

Au-delà de l'ortho-typographie, une assistance IA peut analyser le style, la syntaxe et la bibliographie (voir [`docs/CATALOGUE_REGLES_IA.md`](docs/CATALOGUE_REGLES_IA.md)). Chaque lancement exige un choix explicite parmi trois modes — aucun n'est mémorisé d'une fois sur l'autre :

- **Désactivée** : comportement inchangé, seul le moteur déterministe s'exécute.
- **Locale (Ollama)** : indiquer le nom exact du modèle chargé dans Ollama (`ollama list`). Aucune donnée ne quitte le poste de travail.
- **Distante (API)** : Gemini ou Groq, avec une clé API. Le texte des paragraphes analysés est envoyé à un service tiers — un avertissement de confidentialité s'affiche à chaque lancement dans ce mode, à confirmer explicitement.

Les suggestions de la couche IA ne modifient jamais le texte : elles apparaissent en surlignage jaune foncé, accompagné d'un commentaire Word expliquant la proposition (voir [`docs/NOTICE_COULEURS_WORD.md`](docs/NOTICE_COULEURS_WORD.md)).

En ligne de commande, sans interface :

```bash
python -m purh_editorial.corrector.cli chemin\vers\source.docx chemin\vers\sortie.docx
```

## 6. Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

## 7. Documentation complémentaire

- [Architecture du correcteur (stratégie actuelle)](docs/REBORN_ARCHITECTURE.md)
- [Catalogue des 61 règles éditoriales](docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md)
- [Code couleur des surlignements Word](docs/NOTICE_COULEURS_WORD.md)

L'architecture antérieure (pivot Python‑JSON, scoring, seuils, exports multiples, IA multi-niveaux) a été abandonnée après plusieurs refontes infructueuses et intégralement supprimée du dépôt. Sa documentation reste consultable à titre d'archive dans [`docs/legacy/`](docs/legacy/README_PIVOT_ARCHITECTURE.md).
