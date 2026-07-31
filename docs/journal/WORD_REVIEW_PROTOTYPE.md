# Prototype de document de revision Word

Cette passe ajoute une preuve technique isolee pour produire un troisieme
document DOCX de revision a partir de deux fichiers sources :

```text
document_original.docx
document_corrige_candidat.docx
        -> document_revision.docx
```

La creation des revisions est deleguee a la comparaison native de Microsoft
Word. Le projet ne reconstruit pas un diff Word en Python.

## Pre-requis

Le service fonctionne uniquement sous Windows avec Microsoft Word installe et
pilotable par COM. La dependance Python Windows est :

```text
pywin32>=306; platform_system == "Windows"
```

L'import de `win32com` est tardif : importer `purh_editorial` ou lancer la
suite de tests standard ne requiert ni Word ni pywin32 sur les autres
plateformes.

## Contrat du service

L'API publique minimale est :

```python
from pathlib import Path

from purh_editorial.services.word_review_service import WordReviewService

result = WordReviewService().create_review_document(
    original_path=Path("original.docx"),
    revised_path=Path("corrige.docx"),
    output_path=Path("revision.docx"),
)
```

Le service ouvre l'original et le candidat en lecture seule lorsque Word le
permet, ne les ajoute pas aux fichiers recents, ne les sauvegarde jamais et les
ferme avec `SaveChanges=False`.

Il cree une instance Microsoft Word isolee avec `DispatchEx`. Cette instance
n'est pas rattachee a une fenetre Word deja ouverte par l'utilisatrice. Le
service ferme uniquement les documents qu'il a ouverts et quitte uniquement
l'instance qu'il a creee.

## Parametres de comparaison

La comparaison Word est demandee avec :

- destination : nouveau document ;
- granularite : caractere ;
- comparaison de la casse : activee ;
- comparaison des espaces : activee ;
- comparaison du formatage : desactivee ;
- tableaux, notes, en-tetes/pieds, zones de texte et champs : actives ;
- commentaires : desactives ;
- deplacements : desactives ;
- auteur des revisions : `PURH Editorial`.

La comparaison du formatage est volontairement desactivee, car le DOCX candidat
peut etre reconstruit par le pipeline et produire beaucoup de bruit stylistique.

## Ecriture sure

Word enregistre d'abord le document de revision dans un fichier temporaire
voisin de la destination finale. Lorsque l'enregistrement est termine et que le
document temporaire existe, le service remplace atomiquement la destination avec
`os.replace`.

Ainsi, une ancienne sortie valide n'est remplacee qu'apres succes. En cas
d'erreur, le temporaire est supprime et l'ancienne sortie n'est pas effacee.

## Detection des revisions

La fonction independante `document_contains_tracked_changes(path)` inspecte le
DOCX comme une archive ZIP et recherche dans les parties XML `word/*.xml` les
elements de revision Word suivants :

```text
w:ins
w:del
w:moveFrom
w:moveTo
```

Elle retourne `False` pour un DOCX valide sans revisions et leve une
`WordReviewError` pour un fichier illisible ou qui n'est pas un DOCX valide.

## Outil manuel

La commande minimale est :

```text
python -m purh_editorial.word_review ORIGINAL.docx CANDIDAT.docx REVISION.docx
```

Depuis ce checkout non installe, definir d'abord `PYTHONPATH=src` ou installer le
paquet en mode editable.

Elle affiche le chemin du document cree et indique si des modifications suivies
ont ete detectees.

## Raccordement au pipeline

`Step1Options.output_path` produit le DOCX candidat corrige par le pipeline.
`Step1Options.word_review_output_path` demande ensuite le DOCX de revision
Word. Ces deux chemins doivent etre distincts.

Le raccordement exige une source DOCX et Microsoft Word sous Windows. Le
pipeline appelle la comparaison seulement apres l'export effectif du candidat.
Si Word echoue ou est indisponible, le candidat deja produit est conserve ;
l'echec est consigne dans le rapport du pipeline.

## Test d'integration reel

Le test d'integration avec Microsoft Word est volontairement facultatif :

```text
PURH_RUN_WORD_INTEGRATION=1 py -m pytest tests/integration/test_word_review_integration.py
```

Il est ignore si la variable n'est pas definie, si la plateforme n'est pas
Windows ou si Microsoft Word n'est pas disponible.

## Limites de cette passe

Cette preuve technique ne traite pas l'interface graphique, les commentaires
Word, les couleurs de revision, les boutons accepter/rejeter, les macros, la
reprise de session editoriale ni l'injection de suggestions IA. Elle ne couple
pas encore le service au pipeline PURH.
