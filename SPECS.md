# SPECS.md

## 1. Objet

Le projet vise à construire une chaîne modulaire de préparation éditoriale pour les PURH.

Cette chaîne doit permettre :
- de contrôler un manuscrit sur le plan orthotypographique ;
- de produire des diagnostics structurés ;
- d'offrir des suggestions stylistiques prudentes ;
- de préparer le texte à une structuration Métopes / XML ;
- d'exploiter ou transformer un XML Métopes vers HTML et PDF.

---

## 2. Finalité

Le système n'a pas pour but de remplacer l'éditrice ou l'éditeur.
Il a pour but :
- d'automatiser ce qui relève de règles explicites ;
- d'assister ce qui relève d'un jugement prudent ;
- de rendre plus fluide le passage du manuscrit vers une forme structurée et publiable.

---

## 3. Modules fonctionnels

## 3.1 Module A — Ingestion et normalisation initiale
### Rôle
Recevoir un document source ou un extrait et produire une représentation interne exploitable.

### Entrées possibles
- DOCX ;
- TXT ;
- XML ;
- éventuellement autres formats via conversion en amont.

### Sorties
- `Document` interne ;
- journal minimal d'ingestion ;
- diagnostics de structure ou de lecture.

### Hors périmètre actuel
- import exhaustif de tous les objets Word complexes ;
- conversion universelle et parfaite de tous les formats bureautiques.

---

## 3.2 Module B — Contrôle orthotypographique
### Rôle
Détecter des anomalies ou écarts à des règles formelles explicites.

### Exemples de contrôles
- espaces avant `: ; ? !` ;
- guillemets ouvrants / fermants ;
- appel de note et ponctuation ;
- italiques non appariés ;
- usages de siècles, dates, numéros ;
- doubles espaces ;
- cohérences élémentaires.

### Sorties
- diagnostics structurés ;
- éventuellement propositions de correction locale ;
- rapport global de conformité.

### Règle
Aucune correction silencieuse.
Toute correction doit être :
- localisée ;
- explicable ;
- désactivable.

---

## 3.3 Module C — Suggestions stylistiques assistées par IA
### Rôle
Repérer localement des formulations perfectibles.

### Entrées
- segments textuels ;
- contexte minimal ;
- politique de suggestion ;
- éventuellement diagnostics déjà connus.

### Sorties
- suggestions motivées ;
- niveau de confiance ;
- degré de prudence ;
- proposition alternative éventuelle ;
- possibilité d'abstention.

### Limites
Ce module ne produit pas une "réécriture du livre".
Il ne doit pas :
- lisser la voix de l'auteur ;
- imposer un registre ;
- corriger des choix savants ou disciplinaires non fautifs.

---

## 3.4 Module D — Reconnaissance / préparation de structures
### Rôle
Identifier ou normaliser des structures utiles à la conversion Métopes / XML.

### Structures potentielles
- titre ;
- sous-titre ;
- intertitre ;
- note ;
- citation en bloc ;
- épigraphe ;
- liste ;
- bibliographie ;
- annexe.

### Sorties
- annotations structurelles ;
- enrichissement du `Document` ;
- diagnostics de structure ambiguë.

---

## 3.5 Module E — Passage vers un XML de travail compatible Métopes
### Rôle
Produire, enrichir ou contrôler une représentation XML conforme au périmètre retenu.

### Sorties
- XML de travail ;
- diagnostics de mapping ;
- journal des choix opérés.

### Attention
Les mappings réels devront être fondés sur :
- des exemples XML réels ;
- les usages Métopes effectivement retenus par le projet.

---

## 3.6 Module F — Visualisation XML → HTML / PDF
### Rôle
Transformer un XML Métopes en rendus lisibles pour :
- vérification ;
- circulation interne ;
- publication de travail ;
- contrôle de structure.

### Sorties
- HTML ;
- PDF ;
- diagnostics de rendu si nécessaire.

### Fonction secondaire
Mettre en évidence indirectement les problèmes de structuration.

---

## 4. Distinction fondamentale des régimes d'action

Le système doit distinguer rigoureusement :

### 4.1 Diagnostic
Signalement d'un point à examiner.

### 4.2 Suggestion
Proposition facultative, non imposée.

### 4.3 Correction locale proposée
Transformation déterministe possible sur règle explicite.

### 4.4 Validation humaine
Décision finale sur l'acceptation ou le rejet.

---

## 5. Pipeline cible

Le pipeline de référence pourra être :

1. ingestion ;
2. normalisation minimale ;
3. contrôle orthotypographique ;
4. suggestions stylistiques ;
5. reconnaissance / préparation structurelle ;
6. production ou contrôle XML ;
7. visualisation HTML / PDF.

Mais l'architecture doit aussi permettre :
- l'exécution d'un seul module ;
- la réutilisation indépendante de certains modules ;
- le saut volontaire de certaines étapes.

---

## 6. Formats et échanges

### Modèle interne
Dataclasses Python.

### Format d'échange
JSON documenté.

### Journalisation
Rapports structurés contenant diagnostics, suggestions, transformations et métadonnées de traitement.

---

## 7. Critères de réussite

Le projet sera jugé satisfaisant si :

- les règles orthotypographiques sont testées et traçables ;
- les suggestions IA restent prudentes et utiles ;
- les structures documentaires essentielles sont reconnues ;
- le passage vers le XML est intelligible ;
- les rendus HTML/PDF servent à la validation éditoriale ;
- l'architecture reste modulaire ;
- les cas réels PURH peuvent être progressivement intégrés sans refonte brutale.

---

## 8. Hors périmètre provisoire

Sauf décision explicite contraire, ne pas inclure d'emblée :

- correction grammaticale massive ;
- réécriture complète ;
- gestion exhaustive de tous les objets Word complexes ;
- PAO complète ;
- import automatisé des fichiers InDesign ;
- optimisation visuelle finale de tout le PDF imprimeur.

---

## 9. Dépendances documentaires nécessaires

Pour stabiliser les implémentations, il faudra disposer de :
- guide typographique PURH ;
- couples manuscrit auteur / manuscrit stylé ;
- exemples XML Métopes réels ;
- exemples de rendus HTML/PDF ;
- éventuellement CSL bibliographique si la bibliographie entre tôt dans le périmètre.
