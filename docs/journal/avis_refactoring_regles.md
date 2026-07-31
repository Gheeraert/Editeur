# Avis sur le plan de refactoring en 4 passes (classification des règles + interface)

Ce rapport commente le plan proposé par ChatGPT en 4 passes (audit, conception, implémentation, interface) pour reclasser les règles éditoriales en « déterministe » / « heuristique ». Il n'implique aucune modification du code — avis uniquement.

## Vue d'ensemble

Le plan est bien structuré dans sa forme (audit → conception → implémentation → interface, chaque passe verrouillée par une validation), mais il repose sur un modèle binaire qui ne colle pas exactement à ce que le code fait réellement aujourd'hui.

## Le problème de fond : le plan confond deux axes qui sont aujourd'hui séparés

Dans `orthotypo_service.py`, le booléen `auto` ne code **pas** une distinction déterministe/heuristique — les 19 règles sont *toutes* déterministes (regex ou table fermée, aucune n'a de score de confiance). Ce que `auto` code, c'est un axe orthogonal : *« la correction a-t-elle une source PURH documentée qui autorise à modifier le texte »*. Le commentaire du code est explicite là-dessus : *« this is deliberately stricter than general French practice »*.

13 des 19 règles orthotypo sont donc **déterministes et non appliquées** (diagnostics à revue humaine), pas parce qu'elles sont incertaines, mais parce que l'équipe éditoriale n'a pas encore tranché qu'elles doivent s'appliquer sans validation humaine.

Si on force le modèle « une règle = déterministe (toujours appliquée) OU heuristique (score + politique) », ces 13 règles n'ont plus de case propre :
- les classer « déterministes » → elles deviennent auto-appliquées, ce qui est un **changement de comportement éditorial silencieux** (exactement ce que la Passe 3 s'interdit explicitement) ;
- les classer « heuristiques » → il faut leur inventer un score de confiance qui n'a aucun sens (une regex qui matche est vraie ou fausse, elle n'a pas de degré de confiance), ce qui est un habillage architectural malhonnête juste pour réutiliser le moteur de décision.

C'est le vrai risque du plan : il n'y a nulle part, dans les 4 passes, un endroit qui force à trancher explicitement ce cas avant d'implémenter.

**Recommandation** : ajouter cette question comme livrable obligatoire de la Passe 1 — pour chacune des 13 règles concernées, décider maintenant (validation humaine, avant la Passe 2) si elle doit devenir auto-appliquée ou rester gated, et si gated, comment la nouvelle architecture représente « déterministe mais non autorisée à s'appliquer sans validation » sans réintroduire un troisième système de prudence par la porte de derrière.

## Deuxième point : la couche structure perd de la nuance si on ne le spécifie pas

Les profils prudent/équilibré/exploratoire ne pilotent pas qu'un seuil : ils pilotent **quatre** seuils par profil (transform/diagnostic × titre/poésie), plus un booléen `auto_apply_diagnostics`, plus la couleur de surlignage.

La Passe 2 doit expliciter comment « un score + un moteur de décision unique » restitue toujours une décision à trois issues (appliquer / signaler / ignorer) et pas seulement deux — sinon la distinction actuelle « transformé en confiance » vs « signalé en commentaire Word » disparaît de fait.

La Passe 4 propose « un curseur unique » côté interface : il faut que la Passe 2 précise la formule qui dérive les seuils multiples actuels à partir de cette valeur unique, sinon c'est improvisé au moment de coder l'UI, trop tard pour une décision qui est en réalité architecturale.

## Troisième point : ne pas mélanger les deux triplets de prudence existants

Il y a aujourd'hui *deux* systèmes distincts nommés avec un vocabulaire proche :
- `conservative/balanced/exploratory` pour la structure heuristique ;
- `conservative/balanced/aggressive` pour l'agressivité de l'arbitrage IA (`structure_ai_arbitrator.py`).

La Passe 1 exclut l'IA du périmètre (« hors IA »), mais la Passe 4 dit « supprimer toute référence aux profils prudent/équilibré/exploratoire » sans préciser qu'elle ne touche pas au second triplet.

**Recommandation** : lever l'ambiguïté maintenant plutôt que de la laisser être découverte en cours de Passe 4.

## Un point positif à souligner

Les modules notes de bas de page et bibliographie n'ont aujourd'hui aucun flag `auto` — tout y est déjà inconditionnellement appliqué. Le refactoring n'a donc aucun risque de régression sur ces deux modules ; toute la complexité et le risque du plan se concentrent sur `orthotypo_service.py` (point 1) et `structure_service.py` (point 2). Ça vaut la peine de le noter dans le rendu de la Passe 1, pour ne pas diluer l'effort sur des modules qui n'en ont pas besoin.

## Une recommandation transverse

Avant la Passe 2, prévoir un filet de sécurité explicite : des tests de caractérisation qui figent la classification actuelle (quelle règle est `auto=True`/`False` aujourd'hui, quels sont les seuils numériques par profil) *avant* toute conception de la nouvelle architecture. Ça donne une preuve automatisée que la promesse « aucun changement de comportement éditorial » de la Passe 3 tient, plutôt que de la vérifier a posteriori sur la lecture du diff.

## Résumé

La mécanique en 4 passes est saine (gating, lecture seule d'abord, branche isolée, tests), mais le modèle « déterministe = toujours appliqué / heuristique = score + politique » proposé par ChatGPT ne correspond pas à ce que fait le code actuel — il manque l'axe « validé pour application automatique » qui est aujourd'hui indépendant du déterminisme. Ce point devrait être tranché avant de lancer la Passe 1, sinon l'audit lui-même butera dessus sans le résoudre.
