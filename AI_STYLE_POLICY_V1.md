# AI_STYLE_POLICY_V1.md

## 1. Objet

Ce document fixe la politique d'usage de l'IA pour le module de suggestions stylistiques.

L'IA intervient comme outil d'assistance prudente, non comme réécriveur automatique. Elle doit rester subordonnée aux règles déterministes, aux vetos structurels, aux zones protégées et à la validation humaine.

---

## 2. Principe central

L'IA ne doit jamais se substituer au jugement éditorial humain.

Elle peut signaler, suggérer, motiver une réserve, proposer une reformulation locale et s'abstenir.

Elle ne peut pas imposer une réécriture, uniformiser un style, modifier silencieusement le texte, traiter toute singularité comme une anomalie, passer outre un veto structurel ou décider seule d'une structure documentaire.

---

## 3. Place de l'IA dans le pipeline

### 3.1 Déterministe

Règles explicites, locales, testées : espace typographique, guillemets, abréviation, siècle, correction ponctuelle sûre.

### 3.2 Heuristique scorée

Règles de reconnaissance avec score, preuves et vetos : candidat titre, poésie, citation, bibliographie, code.

### 3.3 IA locale encadrée

L'IA locale intervient seulement dans une zone grise. Elle reçoit une question fermée, par exemple :

```text
Ce bloc est-il plutôt :
A. un titre
B. un vers
C. un paragraphe ordinaire
D. indécidable
```

Elle ne doit pas réécrire librement.

### 3.4 IA exploratoire ou freestyle

L'IA exploratoire est désactivée par défaut. Elle peut aider à comprendre un cas rare, mais ne doit pas appliquer de transformation. C'est une solution de dernier recours.

---

## 4. Types de problèmes que l'IA stylistique peut examiner

Autorisés : répétitions locales manifestes, lourdeurs syntaxiques rapprochées, ambiguïtés ponctuelles, faux parallélismes, formulations inutilement opaques, redondances rapprochées.

À traiter avec prudence extrême : tournures disciplinaires, phrase longue savante mais maîtrisée, effet de style volontaire, citation ou voix rapportée, prose d'auteur à forte identité, terminologie technique.

À ne pas traiter automatiquement : réorganisation globale, harmonisation générale du ton, simplification systématique, réécriture extensive, correction d'une citation, intervention dans une zone protégée sans règle spécifique.

---

## 5. Zones protégées

L'IA doit respecter les zones protégées : citation ancienne, poésie, code, transcription linguistique, tableau, formule, bibliographie, légende, passage explicitement signalé comme à préserver.

Dans ces zones, l'IA doit par défaut s'abstenir, sauf consigne très précise.

Exemples : ne pas reformuler un vers ; ne pas corriger la ponctuation d'une transcription linguistique ; ne pas améliorer un fragment de code.

---

## 6. Forme attendue des sorties

Chaque suggestion doit idéalement comprendre segment visé, message bref, justification, reformulation locale éventuelle, niveau de prudence, niveau de confiance et possibilité d'abstention.

---

## 7. Règles de prudence

La singularité n'est pas une faute. Les textes de SHS peuvent comporter densité conceptuelle, syntaxe complexe, vocabulaire spécialisé, citations intégrées et choix disciplinaires.

L'IA ne doit pas simplifier par réflexe, ne doit jamais suggérer de modifier une citation sans validation humaine, et doit préférer l'abstention en cas de doute.

L'IA stylistique ne doit pas décider qu'un bloc est un titre, une citation, un vers ou une liste. Ces décisions relèvent du module structurel et de son modèle de décision.

---

## 8. Régimes de sortie recommandés

- Abstention : aucun signalement.
- Signalement seul : passage à examiner, sans texte alternatif.
- Suggestion locale : amélioration limitée et révisable.
- Question de zone grise : pour l'IA locale seulement, réponse limitée à une classification parmi des choix fournis.

---

## 9. Journalisation

Pour chaque passage soumis au module IA, conserver si possible : texte source, contexte, prompt ou gabarit, suggestion produite, niveau de prudence, décision humaine ultérieure, indication de zone protégée, raison d'abstention.

---

## 10. Évaluation qualitative

Les fixtures du module IA devront vérifier : absence de réécriture invasive, pertinence des signalements, capacité d'abstention, qualité des justifications, respect des textes savants, respect des zones protégées.

---

## 11. Exemples de cas tests

Cas pertinents : répétition lexicale locale, phrase réellement confuse, redondance manifeste, ambiguïté pronominale locale.

Cas où l'IA doit s'abstenir : phrase longue mais claire, tournure littéraire délibérée, lexique spécialisé, citation ancienne, vers, code, transcription linguistique, tableau.

---

## 12. Interdits absolus

Ne jamais appliquer automatiquement au texte source une suggestion issue de l'IA sans validation humaine explicite.

Ne jamais utiliser l'IA freestyle comme solution normale à un problème qui devrait être traité par une règle déterministe, une heuristique documentée, une fixture ou un diagnostic humain.

Ne jamais masquer une incertitude sous une transformation silencieuse.
