# Note de cadrage
## Projet : chaîne modulaire de préparation éditoriale assistée pour les PURH

## 1. Contexte

Les Presses universitaires de Rouen et du Havre souhaitent se doter d’un environnement de travail permettant d’assister la correction de copie et la préparation éditoriale des manuscrits, dans une logique à la fois rigoureuse, sobre et modulaire.

Le projet s’inscrit dans une perspective de rationalisation de la chaîne éditoriale : il ne s’agit pas seulement d’automatiser certaines vérifications formelles, mais de construire un ensemble cohérent d’outils capables d’accompagner la transformation progressive d’un manuscrit d’auteur vers un texte structuré, stylé et exploitable dans des formats de publication savants.

Le projet adopte un fonctionnement hybride :
- une couche **déterministe**, développée en Python, pour les contrôles formels et normatifs ;
- une couche **assistée par IA**, limitée à des suggestions prudentes et révisables ;
- une couche **de structuration et de restitution**, articulée à la chaîne Métopes et à des modules de visualisation HTML/PDF.

Le développement sera conduit avec l’appui de **Codex AI**, selon une méthode modulaire et incrémentale déjà éprouvée dans le projet **TEI Studio**.

---

## 2. Finalité du projet

L’objectif est de constituer, pour les PURH, une **chaîne de préparation éditoriale modulaire**, composée de briques indépendantes mais interopérables, permettant :

- de contrôler la conformité orthotypographique d’un manuscrit ;
- de signaler des incohérences ou anomalies éditoriales ;
- de proposer, avec prudence, des suggestions d’amélioration stylistique ;
- de préparer l’intégration du texte dans une chaîne de structuration compatible avec Métopes ;
- de produire ou d’exploiter un XML structuré ;
- de transformer ce XML en visualisations de travail ou de publication, notamment en HTML et PDF.

---

## 3. Principes directeurs

### 3.1 Modularité
Chaque brique fonctionnelle doit pouvoir être développée, testée, documentée et, au besoin, remplacée indépendamment des autres.

### 3.2 Interopérabilité
Les modules doivent dialoguer dans un cadre commun, au moyen de formats d’entrée et de sortie stabilisés, explicites et documentés.

### 3.3 Prudence éditoriale
L’automatisation ne doit jamais effacer le rôle de validation humaine.  
Le système doit distinguer nettement :
- ce qui relève d’une **règle vérifiable** ;
- ce qui relève d’une **suggestion interprétative** ;
- ce qui relève d’une **décision éditoriale humaine**.

### 3.4 Traçabilité
Toute intervention automatique ou semi-automatique doit pouvoir être identifiée, justifiée, relue et, si nécessaire, annulée.

### 3.5 Sobriété technique
Le projet doit privilégier des solutions simples, maintenables, pérennes et bien documentées, plutôt que des dispositifs lourds ou opaques.

---

## 4. Périmètre fonctionnel envisagé

### 4.1 Module de contrôle orthotypographique
Ce module, fondé sur des règles explicites, aura pour fonction de vérifier la conformité du manuscrit à un ensemble de normes définies par les PURH.

Il pourra couvrir, selon le périmètre retenu :
- la ponctuation ;
- les espaces fines et insécables ;
- les guillemets ;
- les capitales et petites capitales ;
- les italiques ;
- les appels de notes ;
- certaines régularités bibliographiques ;
- la cohérence des titres, intertitres, numérotations et éléments paratextuels.

Ce module ne relèvera pas de l’interprétation stylistique, mais du **contrôle formel**.

### 4.2 Module d’analyse stylistique assistée par IA
Ce module exploitera une API d’intelligence artificielle pour repérer, de manière prudente :
- lourdeurs ;
- répétitions ;
- ambiguïtés ;
- formulations maladroites ;
- éventuelles tensions de registre ou de cohérence rédactionnelle.

Les résultats devront être produits sous forme de **suggestions**, jamais comme des réécritures imposées.  
Une attention particulière devra être accordée :
- au respect de la voix de l’auteur ;
- à la non-normalisation abusive des styles savants ;
- à la distinction entre amélioration possible et correction nécessaire.

### 4.3 Module de préparation à la structuration Métopes / TEI
Ce module assurera la transition entre le texte corrigé ou validé et son intégration dans un environnement de structuration compatible avec la chaîne Métopes.

Il pourra inclure :
- la normalisation de certains marqueurs ;
- la préparation ou l’enrichissement de structures attendues ;
- l’aide au stylage logique du manuscrit ;
- l’export ou la transformation vers un XML conforme à un cadre défini.

### 4.4 Module de visualisation XML Métopes vers HTML/PDF
Ce module, déjà amorcé dans un autre projet, sera intégré au dispositif général comme brique autonome.

Il permettra de transformer un XML Métopes en visualisations :
- **HTML**, pour lecture, vérification, circulation interne ou publication ;
- **PDF**, pour contrôle, bon à tirer provisoire, ou restitution de travail.

Ce module aura également une fonction de **validation indirecte** de la structuration : ce que le XML produit réellement se révèlera souvent plus clairement dans ses sorties visuelles que dans l’arbre XML lui-même.

---

## 5. Architecture générale visée

Le projet ne doit pas être conçu comme un programme monolithique, mais comme un **ensemble de composants coordonnés**.

Une architecture cible peut être formulée ainsi :

- un **noyau commun** définit les conventions de données ;
- chaque module reçoit un état du document, produit des diagnostics, suggestions ou transformations ;
- un orchestrateur léger permet, selon les besoins :
  - d’exécuter un seul module ;
  - d’enchaîner plusieurs modules ;
  - de conserver un historique des interventions.

Le cadre commun devra vraisemblablement définir :
- un format pivot ;
- un système commun de diagnostics ;
- un mécanisme d’annotation des corrections et suggestions ;
- une journalisation des traitements ;
- un statut de validation humaine.

---

## 6. Méthode de développement

Le développement reposera sur une logique de **petits modules clairement délimités**, selon une pratique déjà expérimentée dans TEI Studio.

Les principes méthodologiques retenus sont les suivants :
- découpage fonctionnel fin ;
- développement incrémental ;
- tests unitaires et fixtures représentatives ;
- documentation immédiate des conventions ;
- validation régulière sur corpus réels ;
- usage de **Codex AI** comme assistant de développement encadré.

Codex AI interviendra non comme substitut au pilotage du projet, mais comme outil de production modulaire, dans un cadre spécifié avec précision :
- objectifs courts ;
- périmètres clairs ;
- sorties testables ;
- révision humaine systématique.

---

## 7. Livrables attendus

À terme, le projet devra produire :

- un ensemble de modules Python autonomes ;
- une documentation fonctionnelle et technique ;
- un schéma de données commun ou format pivot ;
- un corpus de tests et de fixtures ;
- des exemples d’entrée et de sortie ;
- des visualisations HTML/PDF à partir d’XML Métopes ;
- éventuellement une interface légère d’orchestration ou de pilotage.

---

## 8. Bénéfices attendus

Le projet vise plusieurs gains :

- amélioration de la qualité formelle des manuscrits ;
- homogénéisation des pratiques éditoriales ;
- gain de temps dans les vérifications répétitives ;
- meilleure explicitation des normes internes ;
- meilleure continuité entre correction, structuration et publication ;
- réutilisabilité des modules dans d’autres contextes éditoriaux ;
- capitalisation progressive d’un savoir-faire éditorial numérique propre aux PURH.

---

## 9. Points de vigilance

Plusieurs risques doivent être anticipés :

- confusion entre correction normative et suggestion stylistique ;
- dérive vers un système trop complexe ou trop centralisé ;
- dépendance excessive à une IA non suffisamment cadrée ;
- hétérogénéité des corpus d’entrée ;
- absence de conventions communes entre modules ;
- inflation documentaire ou normative rendant les traitements fragiles ;
- décalage entre XML théorique et usages réels de la chaîne éditoriale.

Le projet devra donc avancer par stabilisation progressive, en privilégiant les cas d’usage réels et les corpus tests représentatifs.

---

## 10. Prochaine étape recommandée

La suite logique consiste à transformer cette note de cadrage en un **cahier des charges modulaire**, précisant pour chaque brique :
- son rôle exact ;
- ses entrées ;
- ses sorties ;
- ses dépendances ;
- ses règles ;
- ses cas de test ;
- ses limites ;
- le niveau de validation humaine requis.
