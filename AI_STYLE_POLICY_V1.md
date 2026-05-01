# AI_STYLE_POLICY.md

## 1. Objet

Ce document fixe la politique d'usage de l'IA pour le module de suggestions stylistiques.

L'IA intervient ici comme **outil d'assistance prudente**, non comme réécriveur automatique.

---

## 2. Principe central

L'IA ne doit jamais se substituer au jugement éditorial humain.

Elle peut :
- signaler ;
- suggérer ;
- motiver une réserve ;
- proposer une reformulation locale.

Elle ne peut pas :
- imposer une réécriture ;
- uniformiser un style ;
- modifier silencieusement le texte ;
- traiter toute singularité comme une anomalie.

---

## 3. Types de problèmes qu'elle peut examiner

### Autorisés
- répétitions locales manifestes ;
- lourdeurs syntaxiques proches ;
- ambiguïtés ponctuelles ;
- faux parallélismes ;
- formulations inutilement opaques ;
- redondances rapprochées.

### À traiter avec prudence extrême
- tournures marquées par une discipline ;
- phrase longue savante mais maîtrisée ;
- effet de style volontaire ;
- citation ou voix rapportée ;
- prose d'auteur à forte identité.

### À ne pas traiter automatiquement
- réorganisation globale de paragraphes ;
- harmonisation générale du ton ;
- simplification systématique du style ;
- réécriture extensive d'un chapitre ;
- "amélioration littéraire" non motivée.

---

## 4. Forme attendue des sorties

Chaque suggestion doit idéalement comprendre :
- le segment visé ;
- un message bref ;
- une justification ;
- éventuellement une reformulation locale ;
- un niveau de prudence ou de confiance.

### Exemple
- Segment : phrase du paragraphe X
- Signalement : répétition rapprochée de `toutefois`
- Justification : redondance locale susceptible d'alourdir la lecture
- Proposition : reformulation légère ou suppression d'une occurrence
- Prudence : élevée

---

## 5. Règles de prudence

### 5.1 Préserver la voix de l'auteur
La singularité n'est pas une faute.

### 5.2 Préserver les écritures savantes
Les textes de SHS peuvent comporter :
- densité conceptuelle ;
- syntaxe complexe ;
- vocabulaire spécialisé ;
- citations intégrées.

L'IA ne doit pas "simplifier" par réflexe.

### 5.3 Préserver les citations
Ne jamais suggérer de modifier une citation sans signalement explicite.

### 5.4 Préserver l'incertitude
En cas de doute, préférer :
- l'abstention ;
- ou une suggestion formulée comme hypothèse.

---

## 6. Régimes de sortie recommandés

### A. Abstention
Aucun signalement n'est produit.

### B. Signalement seul
Le système indique qu'un passage mérite attention, sans proposer de texte alternatif.

### C. Suggestion locale
Le système propose une amélioration limitée, explicitement révisable.

---

## 7. Ce qu'il faut journaliser

Pour chaque passage soumis au module IA, conserver si possible :
- le texte source ;
- le prompt ou gabarit de consigne ;
- la suggestion produite ;
- le niveau de prudence ;
- la décision humaine ultérieure.

---

## 8. Évaluation qualitative

Les fixtures du module IA devront permettre de vérifier :
- l'absence de réécriture invasive ;
- la pertinence des signalements ;
- la capacité d'abstention ;
- la qualité des justifications ;
- le respect des textes savants.

---

## 9. Exemples de cas tests à prévoir

### Cas pertinents
- répétition lexicale locale non motivée ;
- phrase à double subordination réellement confuse ;
- redondance manifeste.

### Cas où l'IA doit s'abstenir
- phrase longue mais claire ;
- tournure littéraire délibérée ;
- lexique spécialisé ;
- citation ancienne.

---

## 10. Interdit absolu

Ne jamais appliquer automatiquement au texte source une suggestion issue de l'IA sans validation humaine explicite.
