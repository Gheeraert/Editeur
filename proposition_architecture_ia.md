# Proposition d'Architecture — Couche IA pour PURH Editorial Studio

**Objet :** Intégration d'une couche d'Intelligence Artificielle (LLM) pour l'assistance à la correction stylistique, la normalisation bibliographique et les analyses sémantiques complexes, sans coût d'utilisation et sans rompre avec les principes du moteur `reborn`.

---

## 1. Philosophie & Principes Directeurs

Pour réussir l'intégration de l'IA dans l'outil des Presses universitaires de Rouen et du Havre sans reproduire les écueils de l'ancienne architecture "Legacy", l'IA doit impérativement respecter les règles suivantes :

1. **Rôle d'Assistant, jamais d'Arbitre Silencieux :** L'IA ne doit **jamais modifier le texte de manière transparente ou autonome**. Toute intervention de l'IA doit être formulée sous forme de **suggestion** ou de **diagnostic** (surlignage couleur + commentaire Word).
2. **Confidentialité absolue des manuscrits :** Les tapuscrits des auteurs contiennent des travaux inédits, parfois soumis au secret de la recherche ou sous embargo. L'utilisation d'APIs tierces payantes ou publiques pose des problèmes de RGPD et de propriété intellectuelle. La priorité absolue doit aller aux **modèles exécutés 100 % en local** sur la machine de l'éditrice.
3. **Architecture Opt-in & Tolérante aux Pannes (Graceful Degradation) :** Le moteur déterministe (orthotypographie, espaces, siècles, notes) doit pouvoir fonctionner seul sans IA. Si l'IA n'est pas installée ou si le serveur local ne répond pas, le programme continue de fonctionner normalement sans planter.
4. **Zéro Coût Financier (0 €) :** Exploitation exclusivement d'outils open source, de modèles libres de droits et d'infrastructures d'exécution locales ou de tiers gratuits.

---

## 2. Cas d'Usage Éditotiaux Ciblés

L'IA ne doit pas remplacer les règles déterministes (les regex sont plus rapides, exactes à 100 % et économes en ressources pour les guillemets ou les espaces). Elle doit intervenir **uniquement là où les règles déterministes échouent** :

### 2.1 Normalisation et Parsing Bibliographique Complexe
- **Problème :** Les auteurs rédigent leurs bibliographies sous des formes extrêmement disparates (ex: *"Dupont Jean, Le Titre, PUF, 2020"* vs *"DUPONT (J.), 2020, Le Titre..."*).
- **Apport de l'IA :** Un LLM excelle à extraire la structure sémantique d'une référence complexe en JSON :
  $$\text{Référence brute} \xrightarrow{\text{LLM}} \{\text{auteur}, \text{prénom}, \text{titre}, \text{éditeur}, \text{année}, \text{ville}\}$$
- **Action Word :** Reconstruire la référence au format canonique PURH, appliquer la correction en surlignage jaune et insérer un commentaire explicatif si des éléments (ex. la ville ou l'éditeur) sont manquants.

### 2.2 Améliorations de Style et Repérage de Coquilles Sémantiques
- **Lourdeurs et répétitions :** Détections de pléonasmes, de répétitions abusives ou de formulations passives très lourdes dans les articles scientifiques.
- **Accords complexes en contexte :** Détection de ruptures de construction (anacoluthes), de solécismes ou d'ambiguïtés de grammaire que les correcteurs orthographiques classiques ne voient pas.
- **Action Word :** Surlignage **turquoise** (diagnostic) avec un **commentaire Word natif** (`Comment.Add`) proposant la reformulation suggérée par l'IA.

### 2.3 Vérification des Registres de Langue & Terminologie Spécifique
- Vérification de la cohérence de la terminologie scientifique ou historique à travers tout le manuscrit (ex. variante d'orthographe d'un nom propre de concept ou de personnage historique).

---

## 3. Choix des Solutions Techniques Gratuites (Sans Frais)

### 3.1 Option Privilégiée : Exécution 100 % Locale avec Ollama

**[Ollama](https://ollama.com/)** est aujourd'hui le standard de fait pour exécuter des modèles de langage open source sur un poste de travail (Windows / macOS / Linux) sans aucune connaissance technique préalable.

- **Installation :** Un simple fichier d'installation Windows (`OllamaSetup.exe`). Il fonctionne comme un service en arrière-plan et fournit une API REST locale sur `http://localhost:11434`.
- **Modèles recommandés (100 % gratuits et libres) :**
  1. **`qwen2.5:7b-instruct`** ou **`qwen2.5:14b-instruct`** : Actuellement le meilleur modèle open source pour le traitement du français, le suivi d'instructions strictes et le rendu JSON structuré.
  2. **`mistral:7b-instruct`** : Modèle d'origine française, excellent en grammaire et rédaction.
  3. **`llama3.1:8b-instruct`** : Très polyvalent et rapide.
- **Matériel requis :** Un PC récent (8 à 16 GB de RAM). Les modèles 7B tournents très bien sur processeur (CPU) ou carte graphique grand public (Nvidia/AMD/Intel).

### 3.2 Option Alternative : Tiers Gratuits d'APIs (Cloud)
Si le poste de travail de l'éditrice n'a pas la puissance nécessaire pour faire tourner un modèle 7B local :
- **Groq Free Tier (`llama-3.1-8b-instant`) :** Offre un quota gratuit d'une vitesse fulgurante (~500 tokens/s).
- **Hugging Face Inference API (Gratuit) :** Accès gratuit aux modèles hébergés sur le Hub.
- **Google Gemini Free Tier :** Clé API gratuite via Google AI Studio avec des quotas généreux pour un usage d'édition.

---

## 4. Architecture d'Implémentation dans PURH Studio (`reborn`)

L'intégration doit venir étendre `src/purh_editorial/corrector/` de manière propre et modulaire.

```text
src/purh_editorial/corrector/
├── ai/
│   ├── __init__.py
│   ├── client.py           # Client Ollama / API générique HTTP (requests/httpx)
│   ├── prompts.py          # Prompts système optimisés pour l'édition PURH
│   └── processors/
│       ├── style_checker.py # Détecteur de lourdeurs / propositions de réécriture
│       └── biblio_parser.py # Structuration sémantique de bibliographie
```

### 4.1 Modèle de Données des Suggestions IA
L'IA doit toujours retourner une réponse structurée au format JSON pour éviter toute hallucination de formatage :

```json
{
  "has_suggestion": true,
  "original_text": "Il s'avère avéré que...",
  "suggested_text": "Il est avéré que...",
  "category": "style",
  "explanation": "Pléonasme : 's'avérer avéré' est une redondance."
}
```

### 4.2 Insertion des Commentaires Word via COM (`pywin32`)

L'API Win32COM de Microsoft Word permet d'attacher un vrai **Commentaire Word** à une plage de texte (`Range`). C'est la méthode idéale pour les conseils de style :

```python
# Exemple d'implémentation dans word_document.py
def _add_ai_suggestion_comment(paragraph, start, end, explanation, suggestion):
    target = _exact_range(paragraph, start, end)
    # Surlignage turquoise (diagnostic)
    target.HighlightColorIndex = WD_TURQUOISE 
    # Ajout du commentaire Word natif
    comment_text = f"[PURH IA - Suggestion] : {explanation}\n\nProposition : \"{suggestion}\""
    paragraph.Range.Comments.Add(Range=target, Text=comment_text)
```

---

## 5. Exemple Concret de Workflow pour l'Éditrice

1. **Lancement de l'UI :** L'éditrice ouvre `main.py`. Une nouvelle case à cocher apparaît : `[ ] Activer l'assistance stylistique & bibliographique par IA (Ollama)`.
2. **Exécution :**
   - Le moteur déterministe applique immédiatement les 38 règles ortho-typographiques (jaune).
   - En second passage, le module IA analyse les paragraphes complexes et les sections bibliographiques.
3. **Résultat dans Word :**
   - L'éditrice retrouve son document avec les surlignements jaunes.
   - Les passages posant un problème de style ou de bibliographie incomplète sont surlignés en **turquoise**, avec une bulle de commentaire Word sur le côté droit que l'éditrice peut valider ou refuser d'un simple clic (`Accepter la modification` ou `Supprimer le commentaire`).

---

## 6. Feuille de Route d'Implémentation Suggérée

1. **Phase 1 (Validation POC - 1 jour) :**
   - Installer Ollama localement et tester le modèle `qwen2.5:7b-instruct` sur 10 exemples de bibliographies complexes et de phrases lourdes de corpus PURH réels.
2. **Phase 2 (Module Client Python - 2 jours) :**
   - Créer `src/purh_editorial/corrector/ai/client.py` effectuant un appel HTTP vers `http://localhost:11434/api/generate` avec gestion de fallback (si Ollama n'est pas lancé, le programme saute l'étape IA sans erreur).
3. **Phase 3 (Branchement Word COM - 2 jours) :**
   - Ajouter le support des commentaires Word (`Comments.Add`) dans `word_document.py`.
4. **Phase 4 (Interface & Options - 1 jour) :**
   - Ajouter l'option d'activation dans `gui.py` et mettre à jour la documentation (`docs/NOTICE_COULEURS_WORD.md` et `README.md`).
