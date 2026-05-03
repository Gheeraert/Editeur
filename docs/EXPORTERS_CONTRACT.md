# Contrat des exporteurs

## 1. Objet

Ce document fixe les règles communes aux exporteurs du projet PURH Editorial Studio : DOCX, XML‑TEI Métopes, LaTeX, HTML, PDF ou tout autre rendu futur.

Un exporteur n'est pas un module de reconnaissance structurelle. C'est un renderer.

---

## 2. Principe central

```text
Les exporteurs manifestent le pivot. Ils ne le corrigent pas.
```

Tout exporteur reçoit un `Document` déjà importé, corrigé, structuré, canonicalisé et validé. Il produit une représentation cible.

Il ne doit pas :

- décider qu'un bloc est un titre ;
- décider qu'un bloc est un vers ;
- décider qu'un bloc est une bibliographie ;
- réparer silencieusement un état incohérent ;
- introduire une sémantique absente du pivot ;
- masquer un défaut de canonicalisation.

---

## 3. Ce qu'un exporteur peut faire

Un exporteur peut :

- convertir un type canonique dans le format cible ;
- appliquer le style de rendu correspondant ;
- préserver les inlines, notes, tableaux et retours de ligne selon le contrat ;
- produire un diagnostic si le pivot est incomplet ;
- utiliser un fallback explicite et documenté lorsqu'un format cible ne permet pas une représentation parfaite.

---

## 4. Ce qu'un exporteur ne doit pas faire

Un exporteur ne doit pas contenir d'heuristique locale du type :

```python
if line_is_short and starts_with_uppercase:
    render_as_heading()
```

ou :

```python
if protected_zone == "poetry" or metopes_style == "TEI_verse":
    render_as_poetry()
```

Ces informations peuvent servir à diagnostiquer une incohérence, mais non à inventer la structure. La structure doit être déjà canonicalisée dans le pivot.


## 4.1 Sémantique explicite seulement

Un exporteur doit consommer la sémantique canonique explicitement inscrite dans le pivot, par exemple `attributes["semantic"]` dans le format transitoire actuel. Il ne doit pas appeler une fonction qui reconstruit silencieusement la sémantique depuis d'anciens marqueurs legacy si cette reconstruction n'a pas été écrite dans le pivot par le canonicalizer.

La compatibilité avec les anciens états du modèle appartient à l'amont : import, canonicalisation, migration ou validation. Elle n'appartient pas aux renderers.

Exemples de clés utilisables comme indices en amont, mais interdites comme source canonique directe dans les exporteurs :

- `quote_kind` legacy ;
- `lineation` legacy ;
- `protected_zone` ;
- `metopes_style` ;
- `style_name` ou `style_id` Word ;
- indentation, blancs, retours de ligne ou apparence visuelle.

Règle courte :

```text
legacy peut aider à canonicaliser ; legacy ne doit pas suffire à exporter.
```

---

## 5. Ordre contractuel avant export

Avant tout export de production, le pipeline doit avoir exécuté :

```text
import
  -> normalisations déterministes sûres
  -> reconnaissance / décisions structurelles
  -> canonicalisation du pivot
  -> validation du pivot
  -> export
```

Un export appelé directement sur un document non canonicalisé doit être considéré comme un usage de debug, non comme une sortie fiable.

---

## 6. Gestion des incohérences

Si un exporteur reçoit :

```json
{
  "attributes": {
    "protected_zone": "poetry"
  }
}
```

ou même un état legacy du type :

```json
{
  "attributes": {
    "quote_kind": "poetry",
    "lineation": "verse"
  }
}
```

mais pas de sémantique canonique explicitement stockée :

```json
{
  "attributes": {
    "semantic": {
      "role": "quote",
      "quote_kind": "poetry",
      "lineation": "verse"
    }
  }
}
```

il ne doit pas deviner. Il doit signaler :

```text
pivot non canonicalisé : indices ou clés legacy de poésie sans sémantique canonique stockée
```

Le traitement correct appartient à la canonicalisation en amont.

---

## 7. Export DOCX

Le DOCX est une sortie de relecture humaine.

Il peut rendre visibles :

- les corrections localisées ;
- les suggestions ;
- les styles Métopes ;
- les citations ;
- les tableaux ;
- les zones protégées.

Mais il n'est pas la vérité du document.

Règle : un rendu DOCX visuellement correct ne prouve pas que le pivot est juste. La cohérence doit être vérifiée dans le JSON canonique et dans les tests d'invariants.

---

## 8. Export XML‑TEI Métopes

L'XML‑TEI est la sortie de production.

Il doit être produit depuis le pivot canonicalisé, non depuis des styles Word ou des heuristiques locales.

Exemple :

```text
pivot attributes.semantic.quote_kind=poetry + attributes.semantic.lineation=verse
  -> <cit><quote><lg><l>...</l></lg></quote></cit>
```

Exemple interdit :

```text
style Word TEI_verse
  -> directement <lg>/<l>
```

Le style Word peut être un fait source ou un indice, mais la décision doit être inscrite dans le pivot avant export.

---

## 9. Export LaTeX

Le LaTeX doit être, à terme, une projection directe du pivot Python‑JSON.

Il peut exister transitoirement une voie :

```text
TEI -> modèle sémantique LaTeX -> LaTeX
```

mais cette voie ne doit pas devenir un second pivot concurrent. La cible architecturale reste :

```text
pivot Python‑JSON -> LaTeX
```

ou, si l'on choisit explicitement de passer par TEI :

```text
pivot Python‑JSON -> XML‑TEI validé -> LaTeX
```

Dans tous les cas, il ne doit pas y avoir de redétection locale de la structure dans le renderer LaTeX.

---

## 10. Export HTML / PDF

HTML et PDF relèvent de la visualisation et du contrôle.

Ils peuvent aider à repérer une erreur de structure, mais ne doivent pas devenir des sources de vérité.

Un défaut visuel doit être analysé ainsi :

1. le pivot est-il correct ?
2. le mapping cible est-il correct ?
3. le renderer est-il correct ?

---

## 11. Tests communs aux exporteurs

Chaque exporteur doit avoir des tests qui vérifient :

- qu'il respecte les types canoniques ;
- qu'il n'ajoute pas de structure absente ;
- qu'il échoue ou diagnostique les incohérences ;
- qu'il conserve les inlines utiles ;
- qu'il respecte les zones protégées ;
- qu'il reste cohérent avec les autres sorties.

Exemple de test transversal :

```text
un bloc pivot canonique "citation en vers"
  -> DOCX : style/rendu vers
  -> XML : <lg>/<l>
  -> LaTeX : environnement ou commande versifiée
```

---

## 12. Formule courte

```text
Un export réussi ne prouve rien si le pivot n'est pas validé.
```
