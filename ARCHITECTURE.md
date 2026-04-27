# ARCHITECTURE.md

## 1. Principe

L'architecture cible est **modulaire**.
Chaque brique doit pouvoir être développée et testée séparément, tout en s'insérant dans un cadre commun.

Le cœur du système repose sur :
- un **modèle métier interne en dataclasses Python** ;
- une **sérialisation JSON** des états et rapports ;
- des **modules spécialisés** ;
- un **orchestrateur léger**.

---

## 2. Schéma général

```text
Source(s)
   ↓
Ingestion / normalisation minimale
   ↓
Document interne (dataclasses)
   ↓
Orthotypographie ─┐
Style IA ─────────┼──> ProcessingReport / annotations / transformations proposées
Structure ────────┘
   ↓
Préparation / contrôle XML Métopes
   ↓
XML de travail
   ↓
Rendu HTML / PDF
```

---

## 3. Pourquoi dataclasses + JSON

### Dataclasses
Elles servent à :
- structurer le modèle métier ;
- expliciter les invariants ;
- rendre le code plus lisible et plus sûr ;
- éviter la dérive vers des dictionnaires hétérogènes.

### JSON
Il sert à :
- sauvegarder un état intermédiaire ;
- fabriquer les fixtures ;
- sérialiser les rapports ;
- comparer des sorties attendues ;
- déboguer.

Le JSON n'est pas la vérité du système, mais son miroir transportable.

---

## 4. Couches du système

## 4.1 Couche modèle
Contient les objets métier :
- `Document`
- `Metadata`
- `Block`
- `Note`
- `BibliographyItem`
- `Diagnostic`
- `Suggestion`
- `Transformation`
- `ProcessingReport`

## 4.2 Couche logique métier
Contient les règles et traitements :
- détection orthotypographique ;
- reconnaissance structurelle ;
- préparation XML ;
- intégration des résultats IA.

## 4.3 Couche I/O
Responsable de :
- lecture des DOCX/TXT/XML ;
- écriture des JSON ;
- export XML/HTML/PDF.

## 4.4 Couche orchestration
Responsable de :
- chaîner les modules ;
- conserver l'état ;
- agréger les rapports ;
- gérer les options d'exécution.

---

## 5. Orchestrateur

L'orchestrateur ne doit pas contenir la logique détaillée des modules.
Il doit seulement :
- charger un document ;
- exécuter un ou plusieurs modules ;
- collecter les rapports ;
- produire un état final ou intermédiaire.

Une interface CLI simple est préférable au départ.
Une interface graphique ou web éventuelle viendra plus tard.

---

## 6. Rapports de traitement

Chaque module doit pouvoir produire un rapport partiel contenant :
- diagnostics ;
- suggestions ;
- transformations proposées ;
- erreurs ;
- avertissements ;
- métadonnées d'exécution.

Ces rapports doivent être fusionnables dans un `ProcessingReport` global.

---

## 7. Identité des segments

Le système devra identifier les portions de texte de façon stable autant que possible.

Objectif :
- rattacher un diagnostic à un segment ;
- comparer avant / après ;
- journaliser une décision ;
- relier un rendu HTML/PDF à une structure source.

Les identifiants peuvent être :
- des ids internes ;
- des chemins logiques (`chapter[1]/paragraph[3]`) ;
- des offsets si nécessaire, mais de préférence pas seuls.

---

## 8. Transformation vs annotation

Deux régimes doivent coexister :

### Annotation
On signale qu'un segment présente un problème ou mérite examen.

### Transformation proposée
On propose un remplacement ou une normalisation.

Cette distinction est cruciale pour ne pas mélanger :
- diagnostic ;
- suggestion ;
- modification effective.

---

## 9. Intégration du module XML → HTML / PDF

Le module de visualisation doit rester autonome.
Il doit idéalement recevoir :
- un XML conforme au périmètre choisi ;
- des options de rendu ;
- éventuellement des ressources associées.

Il ne doit pas dépendre directement du détail du traitement orthotypographique ou IA.

---

## 10. Extensibilité

Le système doit permettre d'ajouter plus tard :
- nouveaux contrôles ;
- nouveaux formats d'entrée ;
- enrichissements bibliographiques ;
- couche d'annotation humaine ;
- interface d'édition / validation.

Cette extensibilité repose sur :
- un modèle stable ;
- des rapports structurés ;
- des frontières nettes entre modules.

---

## 11. Arborescence de code suggérée

```text
src/
  purh_editorial/
    model/
    io/
    orthotypography/
    style_ai/
    structure/
    metopes/
    rendering/
    orchestration/
tests/
  fixtures/
  unit/
  integration/
```

Cette arborescence est indicative et pourra être adaptée, mais l'esprit de séparation doit être conservé.
