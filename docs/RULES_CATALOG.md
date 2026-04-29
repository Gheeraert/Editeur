# RULES_CATALOG (priorités SHS, V1)

Catalogue court (20–30 règles) orienté implémentation prudente.

Légende `Auto` :
- `A1` auto-correction sûre
- `A2` suggestion localisée
- `A3` diagnostic seulement
- `A4` hors périmètre initial

## 1) Espaces et ponctuation

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-SP-001 | PURH p.10 + Lexique (espaces fines) | Espace fine insécable avant `: ; ? !` **en phrase simple** ; ignorer URL, heures, ratios, chemins de fichiers, références techniques | `Bonjour: oui?` | `Bonjour : oui ?` | A1 (restreint) | Moyen | Couvert `purh.espaces.avant_ponct_forte` | phrase simple + garde-fous (URL/heure/ratio/path) |
| R-SP-002 | PURH + usage FR | Supprimer espace avant `,` et `.` | `mot , mot .` | `mot, mot.` | A1 | Faible | Couvert `purh.espaces.avant_ponct_faible` | cas décimaux, ellipses |
| R-SP-003 | PURH (homogénéité) | Réduire doubles espaces | `mot  mot` | `mot mot` | A1 | Faible | Couvert `purh.espaces.double` | espaces mixtes tab/NBSP |
| R-SP-004 | Lexique + IN/PURH | Séparateur des milliers en espace fine insécable | `10 000` | `10 000` | A1 | Moyen | Couvert `purh.nombres.milliers` | années, codes, numéros |

## 2) Guillemets

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-GQ-001 | PURH p.12 | Pour texte FR, préférer `« »` ; conversion des guillemets droits **non toujours sûre** | `"texte"` | `« texte »` | A2 (défaut) / A1 (cas très simples) | Moyen | Couvert `purh.guillemets.droits` | cas simples vs imbriqués/techniques |
| R-GQ-002 | PURH p.12 | Espaces insécables internes des guillemets FR | `«texte»` | `« texte »` | A1 | Faible | Couvert `purh.guillemets.espace_*` | idempotence |
| R-GQ-003 | PURH p.12 + Lexique | Second niveau en guillemets anglais sans espaces | `« « texte » »` | `« “texte” »` | A3 | Élevé | Non couvert | détection imbrication |
| R-GQ-004 | PURH p.12 + Lexique | Ponctuation avant/après guillemet selon citation fondue/non fondue | `« texte ». (cas bloc)` | `« texte. »` | A3 | Élevé | Non couvert | corpus de citations |

## 3) Appels de note

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-AN-001 | PURH p.11 | Appel de note en exposant arabe | `(1)` en ligne | `¹` (ou footnote auto Word) | A3 | Moyen | Partiel (import/export garde superscript) | import DOCX notes |
| R-AN-002 | PURH p.11 + Lexique | Appel avant ponctuation/guillemet fermant ; démarrer en **diagnostic robuste** | `mot.¹` | `mot¹.` | A3 (prioritaire) | Élevé | Non couvert | fin phrase + citation |
| R-AN-003 | PURH p.11 + Lexique | Pas d’espace avant appel; pas de rejet ligne | `mot ¹` | `mot¹` | A3 | Moyen | Non couvert | détection whitespace |

## 4) Notes de bas de page

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-FN-001 | PURH p.5/p.11 | Notes en bas de page (pas fin de volume) | notes fin document | footnotes | A3 | Faible | Partiel (pipeline conserve notes) | structure doc import |
| R-FN-002 | PURH p.5 | Une note = un seul paragraphe | note multi-lignes | note phrase continue | A3 | Moyen | Non couvert | note avec retours ligne |
| R-FN-003 | PURH p.7/p.11 + IN | `ibid./op. cit./loc. cit.` formatés proprement | `Op. cit` | `op. cit.` | A1/A2 | Moyen | Couvert partiel `FootnoteNormalizer` | débuts/fin de note |
| R-FN-004 | PURH (uniformité) | Ajouter point final si note incomplète | `Texte de note` | `Texte de note.` | A1 | Moyen | Couvert `FootnoteNormalizer` | URL/vers exceptions |

## 5) Siècles, ordinaux, exposants

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-SO-001 | PURH p.10 | Siècles en romain + `e` ; la normalisation textuelle seule est insuffisante : cible éditoriale = petites capitales + exposant quand le modèle de spans le permet | `19ème` | `XIXe` (+ style petites caps/exposant si disponible) | A2 | Moyen | Couvert partiel `purh.siecles` (pas smallcaps/exposant) | XIXe, XXIe, faux positifs + style inline |
| R-SO-002 | PURH p.10 | Ordinaux courts (`1re`, `5e`) | `1ère`, `5ème` | `1re`, `5e` | A1 | Moyen | Partiel via `purh.siecles` | 1er/1re/2de |
| R-SO-003 | PURH p.10 + IN | `nᵒ`, `rᵒ`, `vᵒ` (o exposant) | `no`, `ro` | `nᵒ`, `rᵒ` | A3 | Élevé | Non couvert | contexte bibliographique |

## 6) Abréviations courantes

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-AB-001 | PURH p.10 | `etc.` jamais en italique, pas `etc...` | `etc...` | `etc.` | A1/A2 | Faible | Couvert `purh.abreviations.etc` | fin de phrase |
| R-AB-002 | PURH p.10 | Abréviations limitées dans corps du texte | abréviations partout | abréviations surtout notes/réfs | A3 | Élevé | Non couvert | rapport diagnostic |
| R-AB-003 | PURH p.10 | Espaces insécables dans `op. cit.`, `loc. cit.`, `s. l.`, `s. d.` | `op. cit.` (espace normal) | `op. cit.` | A1/A2 | Moyen | Partiel (op/art/loc dans notes) | s.l., s.d. |
| R-AB-004 | PURH p.11 | Ne pas redoubler `pp./vv./ll.` | `pp. 10-20` | `p. 10-20` | A2 | Élevé | Non couvert | bibliographie/notes |

## 7) Capitales, petites capitales, tout-majuscules

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-CA-001 | PURH p.10 + Lexique | Accentuer les capitales | `ECOLE` (pour `École`) | `ÉCOLE` | A2/A3 | Élevé | Non couvert | dictionnaire/lexique |
| R-CA-002 | PURH p.2 | Éviter `TOUT EN MAJUSCULES` pour titres/index/biblio | `CHAPITRE` | `Chapitre` | A3 | Élevé | Partiel structure (détection ALLCAPS) | headings only |
| R-CA-003 | PURH p.10 | Noms de personnes : majuscule initiale seulement | `VICTOR HUGO` | `Victor Hugo` | A3 | Élevé | Non couvert | NER requis |

## 8) Citations courtes et longues

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-CI-001 | PURH p.11-12 | Citation FR fondue : romain + guillemets | *italique* | romain + `« »` | A3 | Élevé | Non couvert | distinctions de langue |
| R-CI-002 | PURH p.11-12 | Citation FR non fondue : romain sans guillemets | `« bloc FR »` | bloc romain sans guillemets | A3 | Élevé | Partiel structure (`quote_block`) | bloc vs inline |
| R-CI-003 | PURH p.11-12 | Citation étrangère fondue : italique + guillemets | romain simple | italique + guillemets | A3 | Élevé | Non couvert | détection langue |
| R-CI-004 | PURH p.11-12 | Citation étrangère non fondue : italique ; traduction romain | traduction absente | traduction ajoutée/placée | A4 | Élevé | Non couvert | intervention auteur |

## 9) Titres et hiérarchie

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-TI-001 | PURH p.4 | Chaîne hiérarchique sans saut de niveau | Titre 1 -> Titre 3 | Titre 1 -> Titre 2 -> Titre 3 | A3 | Moyen | Partiel (`StructurePreparationService`) | suite de headings |
| R-TI-002 | PURH p.4 | Intertitres non numérotés (hors parties) | `1.2.3` partout | titres non numérotés | A3 | Élevé | Partiel heuristique | style source needed |
| R-TI-003 | PURH p.2-4 | Homogénéité de style par niveau | mix gras/italique incohérent | style stable par niveau | A3 | Moyen | Partiel | diagnostics de cohérence |

## 10) Bibliographie

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-BI-001 | PURH p.7-8 | Biblio en fin volume (ou fin article revue) | biblio dispersée | section biblio dédiée | A3 | Faible | Partiel (`BibliographyNormalizer`) | structure volume |
| R-BI-002 | PURH p.8 | Un seul modèle biblio par ouvrage | mélange modèles 1/2 | modèle homogène | A3 | Élevé | Non couvert | détection mixed style |
| R-BI-003 | PURH p.8 | Auteur répété -> tiret cadratin + virgule (modèle 1) | auteur répété complet | `—,` | A2/A3 | Moyen | Non couvert | série d’entrées |

## 11) Cas à ne pas automatiser

| Rule ID | Source observée | Description | Fautif | Attendu | Auto | Risque FP | État code actuel | Tests à prévoir |
|---|---|---|---|---|---|---|---|---|
| R-NA-001 | PURH + AI policy | Réécriture stylistique savante | simplification agressive | diagnostic/suggestion seulement | A4 | Très élevé | IA déjà prudente | non-réécriture |
| R-NA-002 | Lexique (citation) | Choix fin romain/italique/gras en citations complexes | automatisation brutale | validation humaine | A4 | Très élevé | Non couvert | cas limites |
| R-NA-003 | PURH p.8 + IN | Normalisation bibliographique exhaustive multi-cas | reformat total | corrections locales + diagnostics | A4 | Très élevé | Partiel local | fixtures hétérogènes |

## Règles prioritaires à implémenter ensuite (ordre conseillé)

1. `R-AN-002` (appel de note vs ponctuation/guillemets) en diagnostic robuste.
2. `R-GQ-004` (ponctuation autour des guillemets) d’abord en diagnostic.
3. `R-SO-002` (ordinaux `1re/5e`) avec tests anti-faux positifs.
4. `R-AB-003` extension espaces insécables `s. l.`, `s. d.`.
5. `R-BI-002` diagnostic de cohérence de modèle bibliographique.

## Premières règles à implémenter en sécurité

### Tests de garde-fous (d'abord)
- `R-SP-001` : ne pas toucher URL, heures (`12:30`), ratios (`16:9`), chemins (`C:\...`), refs techniques (`RFC 1234:5`).
- `R-GQ-001` : ne pas convertir automatiquement les guillemets imbriqués ou mixtes.
- `R-SO-001` : vérifier qu'on n'altère pas les contextes non-sècles.

### Corrections A1 vraiment sûres
- `R-SP-002` (espace avant `, .`)
- `R-SP-003` (doubles espaces)
- `R-AB-001` (`etc...` -> `etc.`)

### Diagnostics A3 prioritaires
- `R-AN-002` (appel de note vs ponctuation/guillemet)
- `R-GQ-004` (ponctuation de citation)
- `R-BI-002` (cohérence du modèle bibliographique)
