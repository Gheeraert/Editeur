# ARCHITECTURE (V1 consolidee)

## 1. Principes conserves

- modularite stricte ;
- logique metier hors interface ;
- dataclasses comme representation canonique ;
- JSON pour inspection/debug/export pivot ;
- transformations tracables et reversibles ;
- IA optionnelle et prudente.

## 2. Chaine de traitement

```text
Entree (docx/xml/txt)
  -> ingestion (io)
  -> Document (model)
  -> diagnostics formels (services)
  -> normalisation sure (services)
  -> preparation structurelle (services)
  -> suggestions IA (services + provider)
  -> ProcessingReport + payload pivot JSON
  -> UI gauche/droite + exports
```

## 3. Enrichissement documentaire inline

Le modele documentaire est enrichi sans casser la structure existante:
- `InlineStyle` (bold/italic/small_caps/subscript/superscript)
- `InlineSpan` (texte inline + style + note_ref + kind)
- `Block.inlines`
- `Block.note_refs`
- `Note.inlines`

Les objets historiques (`Document`, `Block`, `Paragraph`, `Heading`, `QuoteBlock`, `Note`) restent en place.

## 4. Import DOCX

`io/docx_importer.py` recupere maintenant:
- style de paragraphe ;
- runs inline ;
- flags de style inline ;
- appels de notes dans le corps ;
- contenu de notes de bas de page ;
- styles inline dans les notes.

## 5. Normalisation et preservation inline

`services/normalization_service.py`:
- conserve les spans inline ;
- applique les regles auto sur le texte des spans sans aplatir la structure ;
- trace les transformations avec `attributes.preserved_inline_styles=true`.

## 6. Provider IA Groq

`style_ai/providers/groq_provider.py`:
- parsing defensif de la reponse API ;
- extraction JSON robuste (direct, markdown, reponse bruitee) ;
- gestion payload partiel ;
- erreurs propres via `ProviderError`.

`services/ai_service.py`:
- en cas d'erreur provider sur un passage, warning cible et continuation.

## 7. UI

`ui/app.py`:
- vue gauche/droite en lecture seule ;
- rendu inline des styles ;
- surlignage des blocs modifies ;
- navigation vers blocs cibles depuis les onglets de resultat.

## 8. Extensibilite preservee

- ajout futur de providers IA sans refonte ;
- enrichissement progressif des regles PURH ;
- preparation vers metopisation en conservant l'information inline/note.
