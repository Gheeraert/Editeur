# TEST_STRATEGY.md

## 1. Objet

Définir une stratégie de test compatible avec un développement modulaire, incrémental et assisté par Codex.

---

## 2. Principe général

Le projet doit avancer par couches :

1. tests unitaires sur logique isolée ;
2. tests sur fixtures ciblées ;
3. tests d'intégration entre modules ;
4. tests de non-régression.

Il ne faut pas dépendre d'un unique test "de pipeline complet" pour savoir si le projet tient.

---

## 3. Types de tests

## 3.1 Tests unitaires
Portent sur des fonctions ou classes précises.

### Exemples
- détection d'espace avant `:`
- normalisation de guillemets
- rattachement d'un diagnostic à un bloc
- fusion de rapports
- sérialisation JSON d'une dataclass

## 3.2 Tests sur fixtures
Portent sur un cas métier ciblé.

### Exemples
- cas `quotes_french_spacing`
- cas `note_call_position`
- cas `local_repetition_should_be_flagged`

## 3.3 Tests d'intégration
Vérifient que deux ou trois modules coopèrent correctement.

### Exemples
- ingestion + orthotypographie ;
- ingestion + structure ;
- XML + rendu HTML.

## 3.4 Tests de non-régression
Garantissent qu'un cas déjà résolu ne casse pas lors d'une évolution ultérieure.

---

## 4. Politique de couverture

La couverture n'est pas une fin en soi.
La priorité est :
- la stabilité des comportements critiques ;
- la lisibilité des tests ;
- la présence de cas réels convertis en fixtures.

---

## 5. Ce qui doit être testé en priorité

### Priorité absolue
- modèle de données minimal ;
- sérialisation JSON ;
- règles orthotypographiques simples ;
- format des diagnostics ;
- structure des rapports.

### Priorité forte
- politique d'abstention du module IA ;
- reconnaissance de structures simples ;
- lecture de XML de base ;
- rendu HTML minimal.

---

## 6. Règles de qualité pour les tests

Un bon test doit être :
- petit ;
- explicite ;
- stable ;
- lié à un comportement précis ;
- facile à relire.

Éviter les tests qui échouent pour dix raisons à la fois.

---

## 7. Organisation suggérée

```text
tests/
  unit/
    test_model.py
    test_serialization.py
    test_orthotypography_spacing.py
    test_reports.py
  integration/
    test_ingest_to_orthotypography.py
    test_ingest_to_structure.py
    test_xml_to_html.py
  fixtures/
    ...
```

---

## 8. Gestion des cas ambigus

Certains cas, notamment stylistiques, ne produiront pas toujours une "bonne réponse" unique.

Pour ces cas, préférer des assertions de type :
- présence ou absence de suggestion ;
- type de diagnostic ;
- niveau de prudence ;
- interdiction de réécriture massive.

---

## 9. Non-régression éditoriale

Dès qu'un cas réel PURH important est stabilisé, il doit être converti :
- en fixture ;
- en test de non-régression.

C'est la meilleure défense contre les régressions silencieuses produites par des refontes trop larges.

---

## 10. Dépendance aux sources réelles

Les documents réels servent à comprendre.
Les tests doivent en extraire des cas courts.

Ne pas faire reposer la stabilité du projet sur de gros fichiers opaques difficiles à relire.

---

## 11. Déclenchement recommandé des tests

À chaque tâche Codex significative :
- lancer les tests unitaires concernés ;
- lancer les tests d'intégration directement touchés ;
- mentionner les tests ajoutés ou adaptés dans le compte rendu.
