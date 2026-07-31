> **Statut : document de l'architecture legacy (pivot Python-JSON / scoring / seuils / IA multi-niveaux), non utilisé par le point d'entrée actuel (`main.py`).**
> La stratégie actuelle est décrite dans [`docs/REBORN_ARCHITECTURE.md`](../REBORN_ARCHITECTURE.md). Conservé pour référence historique et récupération ponctuelle de code (voir `docs/REBORN_ARCHITECTURE.md` §10 « Politique de réutilisation »).

# Règles typographiques PURH

Ce fichier a été fusionné avec `/TYPO_RULES_PURH.md` (racine) dans un document de
référence unique, qui documente les 17 règles réellement implémentées dans
`OrthotypoService` avec la nomenclature `purh.xxx.yyy` réellement utilisée dans le code
(description, exemple fautif/attendu, niveau, source) :

→ **[CATALOGUE_REGLES_TYPOGRAPHIQUES.md](../CATALOGUE_REGLES_TYPOGRAPHIQUES.md)**

L'ancienne nomenclature `R-SP-xxx`/`R-AB-xxx`/`R-SO-xxx` de ce fichier ne correspondait
pas aux `rule_id` réels du code (seuls `R-GQ-004`, `R-AN-002`, `R-AN-003` et `R-SO-001`
existent effectivement) ; le nouveau catalogue documente les identifiants tels qu'ils
sont réellement utilisés.

Fusion effectuée en Phase 3 de la feuille de route de consolidation typographique.
