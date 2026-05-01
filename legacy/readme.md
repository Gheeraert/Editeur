# Legacy — héritage Impressions

Ce dossier conserve les fichiers essentiels issus du projet **Impressions**, utilisés comme référence pour développer une sortie **XML-TEI → LaTeX/PDF** dans le projet PURH éditorial.

Ces fichiers constituent une **mémoire de travail** pour Codex. Ils ne sont pas le code actif du projet.

## Règle générale

Les fichiers placés dans `Legacy/` sont des références.

Ils ne doivent pas être importés directement depuis le code actif.

En particulier :

- ne pas faire d’imports du type `from Legacy... import ...` ;
- ne pas modifier ces fichiers pour corriger le projet courant ;
- ne pas dupliquer mécaniquement tout le code ;
- s’en servir comme source pour reconstruire une intégration propre dans `src/`.

## Emplacement attendu

Le dossier `Legacy/` doit être placé à la racine du projet.

Structure recommandée :

```text
projet/
  Legacy/
    README.md
    __init__.py
    config.py
    gui.py
    local_server.py
    normalizer.py
    site_builder.py
    site_structure.py
    tei_loader.py
    utils.py
  src/
  tests/
  README.md
  
  
## Précisions sur les 14fichiers legacy

### __init__.py

Marque le paquet Impressions.

### config.py

Définit la configuration de build.

Élément principal :

BuildConfig

Rôle :

définir le dossier de sortie ;
définir le dossier d’assets ;
gérer une éventuelle quatrième de couverture ;
conserver quelques métadonnées de collection ;
fournir le chemin output_assets_dir.
utils.py

Contient les constantes et fonctions utilitaires communes :

XML_NS
TEI_NS
XI_NS
NSMAP
slugify()
xml_id()
set_xml_id()
short_text()
ensure_dir()
html_escape_attr()

Rôle :

centraliser les namespaces TEI, XML et XInclude ;
produire des slugs stables ;
lire et écrire les xml:id ;
fournir les petits utilitaires partagés par les autres modules.

### tei_loader.py

Charge les fichiers XML-TEI.

Élément principal :

TeiLoader

Méthodes importantes :

load_master()
load_single()

Rôle :

charger un fichier TEI simple ;
charger un fichier maître ;
résoudre les xi:include ;
produire un arbre XML unifié ;
récupérer certaines métadonnées des fichiers inclus ;
produire un LoadReport.

À réutiliser comme point d’entrée XML pour toute sortie LaTeX/PDF.

### normalizer.py

Normalise légèrement l’arbre TEI avant rendu.

Élément principal :

TeiNormalizer

Rôle :

attribuer des xml:id manquants ;
fusionner certains <hi rend="..."> adjacents ;
numéroter les notes ;
repérer les figures, médias et ressources associées ;
produire un NormalizeReport.

Cette étape doit être conservée avant toute transformation LaTeX.

### site_structure.py

Construit la structure éditoriale du livre web.

Élément principal :

SiteStructureBuilder

Objets importants :

SiteMeta
PageDef
NavItem
AuthorEntry

Rôle :

extraire les métadonnées générales du volume depuis le teiHeader ;
identifier les groupes éditoriaux ;
repérer les pages ou unités principales ;
construire une navigation ordonnée ;
produire une représentation exploitable du livre.

Pour une sortie LaTeX, ce module évite de reconstruire l’ordre du livre, les métadonnées et les divisions principales.

### site_builder.py

Orchestre la génération du site web statique.

Élément principal :

SiteBuilder

Rôle :

charger le XML avec TeiLoader ;
normaliser le TEI avec TeiNormalizer ;
construire la structure avec SiteStructureBuilder ;
copier les ressources statiques et les assets ;
écrire le TEI normalisé ;
produire les pages HTML via XSLT ;
produire un rapport de build.

Pour la sortie LaTeX, ce fichier doit être considéré comme le modèle d’orchestration.

Il ne faut pas le recopier tel quel : il faut créer un équivalent spécialisé, par exemple :

LatexBuilder

qui réutilise le même début de chaîne :

TeiLoader → TeiNormalizer → SiteStructureBuilder

puis remplace la fin HTML par :

TEI structuré → modèle sémantique → LatexRenderer
gui.py

Interface graphique Tkinter du prototype Impressions.

Rôle :

choisir un fichier XML maître ;
ajouter éventuellement des fichiers XML indépendants ;
choisir un dossier d’assets ;
choisir un dossier de sortie ;
charger/enregistrer une configuration JSON ;
lancer le build ;
prévisualiser le site généré.

Pour le projet courant, ce fichier sert surtout de référence ergonomique.

### local_server.py

Petit serveur local de prévisualisation HTTP.

Élément principal :

PreviewServer

Rôle :

servir localement le site HTML généré ;
choisir automatiquement un port disponible ;
ouvrir le navigateur.

Ce fichier est utile pour la sortie web, mais n’est pas nécessaire pour la sortie LaTeX/PDF.

Chaîne Impressions existante

La chaîne web d’Impressions suit le schéma suivant :

XML-TEI maître ou fichier XML simple
        ↓
TeiLoader
        ↓
arbre XML unifié
        ↓
TeiNormalizer
        ↓
arbre TEI normalisé
        ↓
SiteStructureBuilder
        ↓
SiteMeta + PageDef + NavItem
        ↓
SiteBuilder
        ↓
fragments HTML produits par XSLT
        ↓
site statique
Chaîne LaTeX/PDF souhaitée

La future sortie LaTeX doit reprendre le début de cette chaîne :

XML-TEI maître ou fichier XML simple
        ↓
TeiLoader
        ↓
TeiNormalizer
        ↓
SiteStructureBuilder

Puis ajouter une fin spécifique :

SiteMeta + PageDef + arbre TEI normalisé
        ↓
modèle sémantique éditorial
        ↓
LatexRenderer
        ↓
fichier .tex
        ↓
PDF LuaLaTeX
Fichiers LaTeX retrouvés à part

Deux autres fichiers issus d’Impressions sont particulièrement importants pour la sortie LaTeX :

### semantic_model.py
### latex_renderer.py

Ils ne font pas partie des 9 fichiers cœur listés ci-dessus, mais ils doivent être conservés eux aussi comme références si l’on veut réactiver la sortie LaTeX/PDF.

Emplacement conseillé :

Legacy/
  latex/
    semantic_model.py
    latex_renderer.py

Leur fonction :

semantic_model.py définit le modèle intermédiaire Book, Division, Paragraph, QuoteBlock, Footnote, etc. ;
latex_renderer.py transforme ce modèle en document LaTeX complet, compilable avec LuaLaTeX.
Ce qu’il ne faut pas réinventer

Codex ne doit pas réécrire de zéro :

le chargement XML ;
la résolution des XInclude ;
la normalisation des xml:id ;
la numérotation des notes ;
l’extraction des métadonnées principales ;
la détection des unités éditoriales principales ;
l’idée d’un modèle sémantique intermédiaire.

Ces éléments existent déjà dans l’héritage Impressions.

Ce qu’il faut développer dans le projet actif

Dans le code actif du projet PURH éditorial, il faudra créer ou adapter des modules propres, par exemple :

src/purh_editorial/latex/
  __init__.py
  latex_builder.py
  tei_to_semantic.py
  latex_renderer.py
  semantic_model.py

Ou, selon l’architecture retenue :

src/purh_editorial/exporters/
  latex_exporter.py

Fonction publique attendue :

export_tei_to_latex(input_xml: Path, output_tex: Path) -> Path
Principe architectural à respecter

La sortie LaTeX ne doit pas être une transformation directe fragile :

XML → chaînes LaTeX bricolées

Elle doit respecter une chaîne en plusieurs couches :

XML-TEI
  ↓
normalisation
  ↓
structure éditoriale
  ↓
modèle sémantique
  ↓
renderer LaTeX

Cette séparation permet :

de conserver un code lisible ;
de tester chaque couche séparément ;
d’éviter les effets de bord typographiques ;
de pouvoir produire plus tard d’autres sorties à partir du même modèle.