# Passe 3 — Architecture cible des règles éditoriales

## 0. Statut et périmètre du document

Ce document est une spécification de conception. Il ne décide ni n’implémente
aucune modification de comportement.

Périmètre :

- orthotypographie générale ;
- notes de bas de page ;
- bibliographie ;
- structure du document ;
- pipeline et configuration non IA.

Hors périmètre :

- IA éditoriale ;
- arbitrage IA structurel ;
- paramètres d’agressivité ou appels aux API IA.

La première migration décrite ci-dessous est obligatoirement à comportement
constant. Elle doit préserver les anomalies caractérisées aussi longtemps
qu’une passe corrective distincte ne les a pas explicitement modifiées.

---

## 1. Principes et définitions

### 1.1 Quatre dimensions indépendantes

Une règle est décrite par quatre dimensions qui ne doivent jamais être
confondues.

1. **Nature** : `deterministic` ou `heuristic`.
2. **Action déclarée** : transformation de texte, stylage, structure,
   diagnostic, contrôle du pipeline ou abstention.
3. **Statut de déploiement** : `active`, `review_only` ou `disabled`.
4. **Issue d’une évaluation** : `apply`, `review` ou `ignore`.

Ainsi :

- une règle déterministe peut rester `review_only` faute de validation PURH ;
- une détection déterministe peut avoir pour action un diagnostic ;
- une règle heuristique `active` n’est appliquée que si son score atteint le
  seuil de sa famille et qu’aucun veto ne s’y oppose ;
- un statut ne constitue ni une nature, ni un score, ni un niveau de prudence.

### 1.2 Déterministe conditionnel

Une règle est déterministe conditionnelle si toutes ses conditions et tous ses
vetos sont binaires, reproductibles et suffisants pour garantir l’action
proposée :

```text
conditions explicites vraies
+ aucun veto binaire
→ action canonique

sinon
→ abstention
```

Une regex, une liste d’exclusions, une zone protégée ou une garde technique ne
rendent pas une règle heuristique par eux-mêmes.

### 1.3 Heuristique

Une règle est heuristique lorsqu’elle combine des indices imparfaits. Elle doit
alors produire un score local à une famille, des indices positifs, des indices
négatifs, des vetos et une justification intelligible.

Le score n’est pas une probabilité mathématique et n’est pas comparable entre
familles sans calibration explicite.

### 1.4 Condition binaire, veto et indice

| Élément | Effet | Exemple |
|---|---|---|
| Condition binaire | Détermine si la règle peut correspondre | caractère exact `:` précédé d’un mot |
| Veto binaire | Interdit l’action indépendamment d’un score | cible dans un bloc `code` protégé |
| Indice positif | Augmente la plausibilité d’une hypothèse | paragraphe court et tout en capitales |
| Indice négatif | Réduit la plausibilité sans l’interdire nécessairement | ponctuation finale d’une phrase |
| Conflit | Oppose deux décisions canoniques | étiquette `Résumé` et rôle existant `keywords` |

Un fait Word, comme un style, du gras ou un retrait, est un indice. Il ne devient
pas une sémantique canonique par simple présence.

### 1.5 Sens de l’issue `apply`

`apply` signifie « exécuter l’action déclarée par la règle ». Cette action n’est
pas nécessairement une mutation :

- `apply` + `text_transform` modifie le texte ;
- `apply` + `style_transform` modifie un stylage ;
- `apply` + `diagnostic` ajoute un diagnostic ;
- `apply` + `pipeline_control` pose un veto ou un coupe-circuit ;
- `apply` + `abstain` journalise une abstention explicite.

`review` signifie que l’action proposée n’est pas exécutée et qu’un objet de
revue humaine est matérialisé. `ignore` signifie qu’aucune action éditoriale
n’est matérialisée, tout en permettant une trace technique minimale.

---

## 2. Modèle de données proposé

La cible utilise des dataclasses et des enums simples. Elle évite une hiérarchie
de sous-classes par famille.

### 2.1 Enums

```python
class RuleFamily(StrEnum):
    ORTHOTYPOGRAPHY = "orthotypography"
    FOOTNOTE = "footnote"
    BIBLIOGRAPHY = "bibliography"
    STRUCTURE = "structure"


class RuleNature(StrEnum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"


class RuleActionType(StrEnum):
    TEXT_TRANSFORM = "text_transform"
    STYLE_TRANSFORM = "style_transform"
    STRUCTURE_TRANSFORM = "structure_transform"
    DIAGNOSTIC = "diagnostic"
    PIPELINE_CONTROL = "pipeline_control"
    ABSTAIN = "abstain"


class DeploymentStatus(StrEnum):
    ACTIVE = "active"
    REVIEW_ONLY = "review_only"
    DISABLED = "disabled"


class DecisionOutcome(StrEnum):
    APPLY = "apply"
    REVIEW = "review"
    IGNORE = "ignore"
```

### 2.2 Source normative

```python
@dataclass(frozen=True, slots=True)
class NormativeSource:
    source_id: str
    authority: str
    title: str
    version: str | None = None
    locator: str | None = None
    validation: str = "documented"
    note: str | None = None
```

`validation` distingue au minimum une source explicitement validée PURH, une
référence générale, un constat de corpus et une règle interne non sourcée. Cette
valeur informe la gouvernance ; elle ne remplace jamais
`DeploymentStatus`.

### 2.3 Descripteur de règle

```python
@dataclass(frozen=True, slots=True)
class RuleDescriptor:
    rule_id: str
    owner_module: str
    family: RuleFamily
    nature: RuleNature
    action_type: RuleActionType
    deployment_status: DeploymentStatus
    normative_sources: tuple[NormativeSource, ...]
    protection_policy_id: str
    score_family: str | None = None
    legacy_aliases: tuple[str, ...] = ()
    test_refs: tuple[str, ...] = ()
    implementation_state: str = "legacy"
```

Invariants du descripteur :

- `rule_id` est stable et unique ;
- `score_family` est obligatoire pour une règle heuristique native ;
- `score_family` est interdit pour une règle déterministe ;
- le statut `active` d’une règle ne peut être modifié par le curseur ;
- le registre ne contient ni regex, ni fonction de mutation, ni seuil métier.

### 2.4 Contexte et protections

```python
@dataclass(frozen=True, slots=True)
class RuleContext:
    document_id: str
    target_refs: tuple[str, ...]
    source_facts: Mapping[str, object]
    canonical_facts: Mapping[str, object]
    protection: "ProtectionDecision"
    compatibility: "CompatibilityContext"


@dataclass(frozen=True, slots=True)
class ProtectionDecision:
    protected: bool
    policy_id: str
    reasons: tuple[str, ...]
    inherited_from: tuple[str, ...] = ()
    legacy_behavior: bool = False
```

Le contexte fourni à une règle est en lecture seule. La mutation est réservée
à l’exécuteur, après décision.

### 2.5 Action proposée

Une seule dataclass couvre les actions communes, avec des champs optionnels
validés selon `action_type`.

```python
@dataclass(frozen=True, slots=True)
class ProposedAction:
    action_type: RuleActionType
    target_refs: tuple[str, ...]
    before: object | None = None
    after: object | None = None
    offset_start: int | None = None
    offset_end: int | None = None
    style_patch: Mapping[str, object] | None = None
    semantic_patch: Mapping[str, object] | None = None
    created_refs: tuple[str, ...] = ()
    deleted_refs: tuple[str, ...] = ()
    merged_refs: tuple[str, ...] = ()
    diagnostic_payload: Mapping[str, object] | None = None
```

L’absence de changement de texte brut n’annule pas une action de stylage.

---

## 3. Interfaces et protocoles

```python
class DeterministicRule(Protocol):
    descriptor: RuleDescriptor

    def evaluate(self, context: RuleContext) -> "DeterministicResult":
        ...


class HeuristicRule(Protocol):
    descriptor: RuleDescriptor

    def evaluate(self, context: RuleContext) -> "HeuristicProposal":
        ...


class ProtectionResolver(Protocol):
    def resolve(
        self,
        *,
        descriptor: RuleDescriptor,
        document: Document,
        target_refs: tuple[str, ...],
    ) -> ProtectionDecision:
        ...


class ThresholdPolicy(Protocol):
    def thresholds(
        self,
        *,
        score_family: str,
        intervention_level: int,
    ) -> "ThresholdPair":
        ...


class RuleRegistry(Protocol):
    def get(self, rule_id: str) -> RuleDescriptor:
        ...

    def all(self) -> tuple[RuleDescriptor, ...]:
        ...

    def validate(self) -> tuple[str, ...]:
        ...


class ActionExecutor(Protocol):
    def execute(
        self,
        *,
        decision: "RuleDecision",
        document: Document,
    ) -> "ExecutionResult":
        ...
```

Le moteur évalue et décide. L’exécuteur applique. Le registre décrit. Le
résolveur de protections pose les vetos. Aucun de ces composants ne dépend de
Tkinter, de Word ou d’un exporteur.

Objets de politique minimaux :

```python
@dataclass(frozen=True, slots=True)
class ThresholdPair:
    review: float
    apply: float


@dataclass(frozen=True, slots=True)
class CompatibilityContext:
    source_config_version: str | None
    legacy_profile: str | None = None
    legacy_decision_mode: str | None = None
    flags: tuple[str, ...] = ()
```

---

## 4. Format des résultats déterministes

```python
@dataclass(frozen=True, slots=True)
class DeterministicResult:
    rule_id: str
    matched: bool
    target_refs: tuple[str, ...]
    proposed_actions: tuple[ProposedAction, ...]
    conditions_met: tuple[str, ...]
    veto_reasons: tuple[str, ...]
    justification: str
```

Invariants :

- `matched=True` exige au moins une action ou une abstention explicite ;
- un veto interdit toute action mutante ;
- un résultat ne modifie jamais directement le document ;
- la règle décrit le constat et l’action canonique, pas son autorisation de
  déploiement.

### 4.1 Frontière appliquée aux cas demandés

| Cas | Proposition de nature cible | Frontière |
|---|---|---|
| Espace avant ponctuation forte | Déterministe conditionnelle | ponctuation et espace attendue sont exactes ; URL, heure, ratio, chemin et syntaxe technique sont des vetos binaires ; hors domaine couvert, abstention |
| Espaces internes aux guillemets français | Déterministe conditionnelle | paire `« »` identifiée et segment non protégé ; citation ou structure non résolue : abstention |
| Civilités | Déterministe conditionnelle | lexique fermé, forme exacte et contexte nominal explicite ; forme étrangère ou ambiguë : abstention |
| Nombres comportant des milliers | Déterministe conditionnelle | token numérique validé ; ISBN, identifiant, date, tableau ou notation spécialisée : veto |
| Pagination | Déterministe conditionnelle | abréviation fermée suivie d’une valeur compatible ; contexte technique : veto |
| Apostrophes et espaces en contexte technique | Déterministe conditionnelle hors zones techniques | le contexte technique est un veto, non un indice pondéré |

Ces propositions ne changent pas leur statut actuel : les règles non validées
restent `review_only`.

---

## 5. Format des décisions heuristiques

```python
@dataclass(frozen=True, slots=True)
class HeuristicEvidence:
    code: str
    value: object
    contribution: float | None
    explanation: str


@dataclass(frozen=True, slots=True)
class HeuristicProposal:
    rule_id: str
    score_family: str
    score: float
    proposed_actions: tuple[ProposedAction, ...]
    target_refs: tuple[str, ...]
    positive_evidence: tuple[HeuristicEvidence, ...]
    negative_evidence: tuple[HeuristicEvidence, ...]
    veto_reasons: tuple[str, ...]
    justification: str
```

Invariants :

- `score` est borné à `[0, 1]` ;
- la formule et sa version sont identifiables par la famille de score ;
- les contributions sont reproductibles ;
- les vetos sont distincts des contributions ;
- une proposition n’exécute rien ;
- une fusion énumère tous les blocs conservés, fusionnés et supprimés.

Les familles initiales sont `heading`, `poetry`, puis, après calibration,
`footnote_form`, `bibliography_structure`, `bibliography_form` et
`quote_structure`. Aucun seuil numérique n’est inventé pour ces nouvelles
familles avant constitution d’un corpus annoté.

---

## 6. Moteur commun à trois issues

### 6.1 Entrées

- `RuleDescriptor` issu du registre ;
- résultat déterministe ou proposition heuristique ;
- `ProtectionDecision` ;
- statut de déploiement publié ;
- niveau global d’intervention heuristique ;
- seuils de la famille concernée ;
- contexte de compatibilité legacy.

### 6.2 Algorithme

```text
si statut == disabled :
    ignore(reason=disabled)

sinon si protection ou veto bloque l’action :
    ignore(reason=protected_or_veto)

sinon si nature == deterministic :
    si aucune correspondance :
        ignore(reason=no_match)
    sinon si statut == review_only :
        review(reason=deployment_review_only)
    sinon :
        apply(action déclarée)

sinon si nature == heuristic :
    si statut == review_only :
        si score >= seuil_review_de_la_famille :
            review
        sinon :
            ignore
    sinon si score >= seuil_apply_de_la_famille :
        apply
    sinon si score >= seuil_review_de_la_famille :
        review
    sinon :
        ignore
```

Le curseur ne peut jamais faire passer une règle `review_only` à `apply`.

### 6.3 Sortie et journal

```python
@dataclass(frozen=True, slots=True)
class RuleDecision:
    decision_id: str
    sequence: int
    rule_id: str
    nature: RuleNature
    deployment_status: DeploymentStatus
    outcome: DecisionOutcome
    target_refs: tuple[str, ...]
    proposed_actions: tuple[ProposedAction, ...]
    reason_code: str
    score_family: str | None
    score: float | None
    review_threshold: float | None
    apply_threshold: float | None
    evidence: tuple[HeuristicEvidence, ...]
    veto_reasons: tuple[str, ...]
    protection: ProtectionDecision
    compatibility_flags: tuple[str, ...] = ()
```

L’exécuteur retourne ensuite :

```python
@dataclass(frozen=True, slots=True)
class ExecutionResult:
    decision_id: str
    applied: bool
    transformations: tuple[Transformation, ...]
    diagnostics: tuple[Diagnostic, ...]
    before_signature: str
    after_signature: str
```

La signature couvre le texte et le style. Elle garantit que les petites
capitales et exposants restent traçables même sans changement du texte brut.

### 6.4 Répartition des responsabilités

| Composant | Responsabilité | Ne doit pas faire |
|---|---|---|
| Règle | détecter, proposer, expliquer | consulter l’interface ou décider son statut |
| Registre | décrire la règle | contenir sa regex ou sa mutation |
| ProtectionResolver | calculer les vetos transversaux | inventer une sémantique |
| ThresholdPolicy | traduire un niveau en seuils familiaux | comparer des scores de familles différentes |
| Moteur | produire `apply/review/ignore` | modifier le document |
| Exécuteur | matérialiser l’action décidée | redécider ou contourner un veto |
| Adaptateur legacy | reproduire le comportement caractérisé | devenir une seconde architecture permanente |

---

## 7. Statuts de déploiement

Le statut publié appartient à une politique éditoriale versionnée, non à la
configuration ordinaire de l’utilisatrice.

- `active` : l’action déclarée peut être exécutée par le moteur ;
- `review_only` : une correspondance peut seulement devenir une revue humaine ;
- `disabled` : la règle n’est pas exécutée ; une trace d’abstention technique
  peut subsister.

Les utilisateurs ne disposent pas d’un interrupteur général permettant
d’activer des règles `review_only`. Une évolution de statut exige une source,
une validation PURH, des tests et une modification explicite du registre.

---

## 8. Niveau d’intervention et seuils par famille

### 8.1 Réglage cible

Configuration non IA proposée :

```json
{
  "editorial_rules": {
    "heuristic_intervention_level": 0
  }
}
```

- entier borné à `0..100` ;
- valeur par défaut : `0`, correspondant au profil historique
  `conservative` ;
- libellé futur : « Niveau d’intervention heuristique » ;
- aucune incidence sur les règles déterministes ;
- aucune incidence sur le statut de déploiement ;
- aucune incidence sur l’IA.

### 8.2 Points d’ancrage historiques

| Niveau | Profil reproduit |
|---:|---|
| `0` | `conservative` |
| `50` | `balanced` |
| `100` | `exploratory` |

Seuils caractérisés :

| Famille | Niveau | Seuil `apply` | Seuil `review` |
|---|---:|---:|---:|
| Titre | 0 | 0,90 | 0,70 |
| Titre | 50 | 0,85 | 0,60 |
| Titre | 100 | 0,75 | 0,50 |
| Poésie | 0 | 0,82 | 0,60 |
| Poésie | 50 | 0,78 | 0,55 |
| Poésie | 100 | 0,72 | 0,48 |

Entre les ancres, l’interpolation est linéaire par famille et par seuil. Les
valeurs hors bornes sont refusées dans la configuration native. La couche de
compatibilité peut conserver temporairement l’ancien comportement de clamp
avec avertissement.

Invariant : `0 <= review_threshold <= apply_threshold <= 1`.

Les familles notes et bibliographie ne reçoivent aucun seuil arbitraire. Elles
restent pilotées par des adaptateurs legacy jusqu’à ce qu’un corpus annoté
permette de fixer des points d’ancrage propres.

### 8.3 Devenir de `auto_apply_diagnostics`

Le modèle cible supprime ce booléen. Pour reproduire temporairement le profil
exploratoire, l’adaptateur traduit son comportement historique ainsi :

```text
ancien diagnostic rendu automatique
→ issue native apply
→ reason_code = legacy_auto_apply_diagnostics
→ effective_apply_threshold = legacy_review_threshold
```

La décision sort donc déjà comme `apply`, `review` ou `ignore`. Aucun diagnostic
ne peut être réappliqué après coup par un booléen indépendant.

---

## 9. Compatibilité avec l’ancien système

### 9.1 Conversion des configurations

| Entrée legacy | Conversion temporaire |
|---|---|
| `heuristic_profile=conservative` | niveau `0` |
| `heuristic_profile=balanced` | niveau `50` |
| `heuristic_profile=exploratory` | niveau `100` + compatibilité `legacy_auto_apply_diagnostics` |
| alias français des profils | même conversion après normalisation existante |
| profil inconnu | niveau `0` + avertissement, comme aujourd’hui |
| seuils titre/poésie explicites | surcharge legacy conservée pour la famille concernée |
| seuil hors `[0,1]` | clamp + avertissement dans l’adaptateur seulement |
| seuil `review > apply` | restauration des seuils du profil + avertissement dans l’adaptateur |
| `decision_mode="deterministic"` | heuristiques scorées désactivées, avec adaptateur reproduisant les transformations résiduelles caractérisées |

Dans la configuration native cible, une contradiction est une erreur claire,
pas une réparation silencieuse.

### 9.2 Priorité et contradictions

1. une configuration native explicite prévaut ;
2. une clé legacy redondante et cohérente produit un avertissement de
   dépréciation ;
3. une clé legacy contradictoire avec la clé native produit une erreur ;
4. les paramètres IA portant un nom proche ne sont ni lus, ni convertis.

### 9.3 Mode historique `deterministic`

Le nom est trompeur : il conserve actuellement le front matter, les promotions
par style source et certaines opérations structurelles. La compatibilité doit
reproduire exactement ce comportement au moyen d’un marqueur interne
`legacy_deterministic_semantics`, sans le présenter comme le sens cible du mot
« déterministe ».

Les nouveaux appels n’exposent pas ce marqueur. Il disparaît après migration
des anciennes configurations et décision explicite sur les promotions
structurelles concernées.

### 9.4 Durée proposée

Maintenir la lecture legacy pendant deux versions de schéma de configuration ou
deux versions mineures publiées, selon la durée la plus longue. Émettre les
avertissements dès la première version et documenter la date de retrait avant
la seconde.

---

## 10. Politique de protections

### 10.1 Première migration : compatibilité stricte

La première implémentation conserve les asymétries caractérisées :

- orthotypographie : protections de bloc et d’inline ;
- notes : protection de la note, de ses inlines et du bloc cible ;
- bibliographie : traitement du type `bibliography_item`, veto seulement sur
  protection explicite ou inline ;
- structure : vetos locaux, sans veto transversal équivalent sur un paragraphe
  explicitement protégé.

Le résolveur porte alors `legacy_behavior=True`. Aucun test ne doit être
« corrigé » pour masquer cette asymétrie.

### 10.2 Politique cible souhaitable

Dans une future passe corrective :

1. une protection explicite est un veto dur pour toute action mutante ;
2. les protections héritées d’un bloc cible s’appliquent à ses notes ;
3. une inline protégée interdit seulement les actions qui intersectent sa
   plage ;
4. un type canonique protégé choisit une politique propre à sa famille ;
5. le propriétaire bibliographique peut normaliser un `bibliography_item`,
   mais jamais un item explicitement protégé ;
6. la structure doit consulter le résolveur avant toute promotion, fusion,
   suppression ou retypage ;
7. une zone protégée reste un veto, pas une sémantique suffisante.

Cette politique exige une passe éditoriale et des tests nouveaux. Elle n’est
pas activée lors du refactoring à comportement constant.

---

## 11. Registre canonique des règles

### 11.1 Organisation

Le registre est une collection unique de `RuleDescriptor`, idéalement dans un
module Python typé et validé au démarrage des tests. Il fournit :

- recherche par `rule_id` ;
- filtre par famille, nature, action et statut ;
- validation d’unicité ;
- contrôle de cohérence nature/score ;
- liens vers sources et tests ;
- état de migration.

La logique fonctionnelle reste dans les modules propriétaires. Le registre
n’embarque ni regex, ni callback de mutation, ni seuil.

### 11.2 Identifiants manquants

Les comportements sans identifiant stable reçoivent, après validation, des
identifiants proposés :

- `structure.bibliography.section.start` ;
- `structure.bibliography.section.end` ;
- `structure.bibliography.item.promote` ;
- `bibliography.entry.detect` pour le helper dormant ;
- `structure.frontmatter.circuit_breaker`.

Ces noms sont réservés par la spécification, mais ne sont pas introduits dans
le code pendant cette passe.

### 11.3 Validation du registre

Les tests futurs doivent échouer si :

- deux règles partagent un identifiant ;
- une règle heuristique n’a pas de famille de score native ou d’adaptateur ;
- une règle déterministe porte une famille de score ;
- une règle `active` sans source validée change de statut sans justification ;
- une règle référencée par une transformation ou un diagnostic est absente.

---

## 12. Table de migration de toutes les règles inventoriées

Légende :

- **Statut refactor** : statut actuel conservé pendant la migration ;
- **Score/adaptateur** : moteur cible et besoin d’un adaptateur à comportement
  constant ;
- **Décision ultérieure** : validation humaine nécessaire avant changement de
  comportement.

### 12.1 Orthotypographie générale

| Règle | Nature cible | Action cible | Statut refactor | Score / adaptateur | Observable à préserver | Décision ultérieure |
|---|---|---|---|---|---|---|
| `purh.apostrophe` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur `auto=False` | diagnostic, texte inchangé, protections | validation normative et contextes techniques |
| `purh.points_suspension` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | diagnostic sans mutation | ellipses savantes et notations |
| `purh.guillemets.droits` | heuristique | diagnostic/proposition | `review_only` | future famille `quote_structure` / adaptateur | diagnostic seulement | distinguer citation, pouces, code, second niveau |
| `R-ORTHO-LIGATURE-OE-001` | déterministe lexicale | texte proposé en revue | `review_only` | aucun / adaptateur | lexique fermé, diagnostic | source PURH acceptable |
| `purh.guillemets.espace_apres_ouvrant` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | diagnostic, zones protégées silencieuses | validation PURH |
| `purh.guillemets.espace_avant_fermant` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | idem | validation PURH |
| `purh.espaces.avant_ponct_forte` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | vetos URL/heure/ratio/chemin, diagnostic | liste fermée des contextes techniques |
| `purh.espaces.avant_ponct_faible` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | décimales exclues, diagnostic | couverture technique |
| `purh.espaces.double` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | diagnostic sans mutation | espaces d’alignement et transcription |
| `purh.civilite` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | lexique et garde actuelle | titres étrangers et bibliographie |
| `purh.siecles` | déterministe | transformation textuelle | `active` | aucun / adaptateur d’ordre | texte, offsets, cible, ordre | aucune activation nouvelle |
| `R-SO-001` | déterministe | stylage | `active` | aucun / adaptateur de signature | petites capitales/exposant même texte identique | aucune |
| `purh.ordinaux` | déterministe | transformation textuelle | `active` | aucun / adaptateur d’ordre | règle active, idempotence | cas souverains hors couverture |
| `purh.tiret.double` | heuristique | diagnostic/proposition | `review_only` | future famille technique / adaptateur | diagnostic, pas de remplacement | sens de `--` |
| `purh.abreviations.etc` | déterministe | transformation textuelle | `active` | aucun / adaptateur d’ordre | texte, ordre, idempotence | aucune |
| `purh.pagination.espace` | déterministe conditionnelle | transformation textuelle | `active` | aucun / adaptateur d’ordre | NNBSP et ordre | périmètre exact validé PURH |
| `purh.numero` | déterministe | texte + stylage | `active` | aucun / adaptateur d’ordre | interaction pagination et règle locale biblio | aucune |
| `R-NO-001` | déterministe | stylage | `active` | aucun / adaptateur de signature | exposant sans exigence de changement brut | aucune |
| `purh.abreviations.redoublement` | déterministe | transformation textuelle | `active` | aucun / adaptateur d’ordre | formes fermées, offsets | aucune |
| `purh.nombres.milliers` | déterministe conditionnelle | texte proposé en revue | `review_only` | aucun / adaptateur | diagnostic, identifiants exclus | valider les vetos binaires |
| `purh.tiret.incise` | heuristique éditoriale | abstention | `disabled` | aucun / adaptateur disabled | aucune transformation | doctrine PURH à trancher |
| `R-TI-001` | déterministe de détection | diagnostic | `review_only` | aucun / adaptateur | diagnostic affirmant l’incertitude, pas une consigne affirmative | formulation et convention |
| `R-GQ-004` | heuristique structurelle | diagnostic | `review_only` | `quote_structure` / adaptateur | diagnostic hors zones protégées | citation fondue/non fondue |

### 12.2 Notes de bas de page

| Règle | Nature cible | Action cible | Statut refactor | Score / adaptateur | Observable à préserver | Décision ultérieure |
|---|---|---|---|---|---|---|
| `purh.note.espace_initiale` | déterministe conditionnelle | texte | `active` | aucun / adaptateur | espaces retirées, ordre, protection | convention import/export |
| `purh.note.majuscule_initiale` | heuristique | texte | `active` | `footnote_form` à construire / adaptateur obligatoire | URL, DOI, particule et latin exclus ; `art. cit.` reste minuscule | corpus annoté et statut futur |
| `purh.note.abreviation_latine` | heuristique provisoire | texte | `active` | `footnote_form` ou reclassification après étude / adaptateur | comportement initial/non initial exact | décider si domaine binaire suffisant |
| `purh.note.espace_op_cit` | déterministe | texte | `active` | aucun / adaptateur | `op.`, `art.`, `loc. cit.` | modèle bibliographique |
| `purh.note.espace_sans_lieu_date` | déterministe | texte | `active` | aucun / adaptateur | `s. l.`, `s. d.` | modèle bibliographique |
| `purh.note.ponctuation_finale` | heuristique | texte | `active` | `footnote_form` à construire / adaptateur obligatoire | DOI reçoit un point ; listes/guillemets exclus | ponctuation selon nature de note |
| `R-AN-002` | déterministe de détection | diagnostic | `review_only` | aucun / adaptateur | texte inchangé, cible et extrait | déplacement éventuellement automatisable |
| `R-AN-003` | déterministe de détection | diagnostic | `review_only` | aucun / adaptateur | peut apparaître sans `R-AN-002` | relation souhaitée entre diagnostics |
| `R-AN-004` | heuristique d’abstention | diagnostic | `review_only` | `footnote_form` / adaptateur | diagnostic URL/particule/latin sans mutation | utilité éditoriale du diagnostic |
| `R-AN-005` | heuristique d’abstention | diagnostic | `review_only` | `footnote_form` / adaptateur | diagnostic URL/vers/liste sans mutation | utilité éditoriale du diagnostic |

### 12.3 Bibliographie

| Règle | Nature cible | Action cible | Statut refactor | Score / adaptateur | Observable à préserver | Décision ultérieure |
|---|---|---|---|---|---|---|
| `structure.bibliography.section.start` proposé | heuristique | contrôle de section | `active` | `bibliography_structure` / adaptateur obligatoire | `Sources de…` ouvre actuellement la section | définir les intitulés canoniques |
| `structure.bibliography.section.end` proposé | heuristique | contrôle de section | `active` | même famille / adaptateur | `Heading 1` brut ne ferme pas actuellement | frontière fondée sur sémantique canonique |
| `structure.bibliography.item.promote` proposé | heuristique | structure + style | `active` | même famille / adaptateur | `paragraph → bibliography_item`, style `BibliographyItem` | validation humaine ou score |
| `bibliography.entry.detect` proposé | heuristique | abstention actuelle | `disabled` | futur score, pas d’adaptateur d’exécution | helper absent du flux | supprimer ou activer dans une passe dédiée |
| `purh.biblio.pagination_nnbsp` | déterministe conditionnelle | texte | `active` | aucun / adaptateur | `rule_id` local dans item bibliographique | source normative |
| `purh.biblio.numero_nnbsp` | déterministe conditionnelle | texte | `active` | aucun / adaptateur | ne pas appeler `purh.numero` | relation avec `nº` canonique |
| `purh.biblio.ponctuation_finale` | heuristique | texte | `active` | `bibliography_form` / adaptateur obligatoire | ajout du point, y compris intention possiblement ouverte | modèle bibliographique PURH |

### 12.4 Structure

| Règle ou famille | Nature cible | Action cible | Statut refactor | Score / adaptateur | Observable à préserver | Décision ultérieure |
|---|---|---|---|---|---|---|
| `structure.frontmatter.abstract` | déterministe conditionnelle | rôle canonique | `active` | aucun / adaptateur | idempotence, rôle antérieur réel, conflit diagnostiqué | définition des étiquettes |
| `structure.frontmatter.keywords` | déterministe conditionnelle | rôle canonique | `active` | aucun / adaptateur | idem | idem |
| `structure.frontmatter.acknowledgment` | déterministe conditionnelle | rôle canonique | `active` | aucun / adaptateur | idem | idem |
| `structure.frontmatter.circuit_breaker` proposé | déterministe de contrôle | coupe-circuit | `active` | aucun / adaptateur | aucune heuristique ultérieure après correspondance | aucune |
| `structure.source_style.heading` | heuristique | structure | `active` | `heading` / adaptateur obligatoire | subsiste en mode legacy deterministic | autorité réelle du style Word |
| `structure.allcaps.heading` | heuristique | structure | `active` | `heading` / adaptateur | score, vetos, ordre | calibration |
| `structure.bold.heading` | heuristique | structure | `active` | `heading` / adaptateur | score, vetos | calibration |
| `structure.italic.author` | heuristique | structure | `active` | `heading` ou famille auteur à calibrer / adaptateur | attribution actuelle | décider rôle auteur |
| `structure.italic.heading` | heuristique | structure | `active` | `heading` / adaptateur | attribution actuelle | calibration |
| `structure.epigraph.heuristic` | heuristique | structure | `active` | famille `epigraph` à construire / adaptateur obligatoire | premier paragraphe court non ponctué | corpus et statut |
| `structure.bibliography.section` | heuristique | contrôle/structure | `active` | `bibliography_structure` / adaptateur | comportement de section actuel | unifier avec normaliseur bibliographique |
| `structure.bibliography.heuristic` | heuristique | structure + diagnostic | `active` | `bibliography_structure` / adaptateur | mutation malgré confiance basse et diagnostic | issue future unique |
| `structure.indent.quote` | heuristique | structure | `active` | `quote_structure` à construire / adaptateur | retrait dominant et promotion | seuil/corpus |
| `structure.quote.guillemets` | heuristique | structure | `active` | `quote_structure` / adaptateur | longueur + guillemets | citation fondue/non fondue |
| `structure.heading.heuristic` | heuristique | structure ou diagnostic | `active` | `heading` natif | seuils et vetos | calibration seulement |
| `R-STRUCT-HEADING-001` | heuristique | décision scorée | `active` | `heading` natif | `transform/diagnostic/ignore` historique | migrer vers `apply/review/ignore` |
| `structure.lineated.blank_bounded.merge` | heuristique | fusion structurelle | `active` | `poetry` à intégrer / adaptateur obligatoire | premier ID conservé, autres supprimés, `merged_from` | automatisation acceptable ? |
| `structure.lineated.short_sequence.merge` | heuristique | fusion structurelle | `disabled` | `poetry`, pas d’exécution | helper non appelé | supprimer ou réintroduire explicitement |
| `R-CI-POETRY-001` | heuristique | décision scorée | `active` | `poetry` natif | seuils, vetos et groupes | calibration |
| `structure.lineated.group.annotate` | heuristique | attributs/diagnostic | `active` | `poetry` / adaptateur | mutation d’attributs possible au niveau diagnostic | séparer proposition et exécution |
| `structure.lineated.stanza.merge` | heuristique | fusion structurelle | `active` | `poetry` / adaptateur | ordre, IDs, blocs supprimés | automatisation acceptable ? |

---

## 13. Stratégie pour les heuristiques sans score

| Famille actuelle | Stratégie de première migration | Cible après validation |
|---|---|---|
| Majuscule initiale de note | adaptateur legacy qui reproduit les branches exactes | score `footnote_form` ou reclassification déterministe sur domaine plus étroit |
| Abréviations latines | adaptateur legacy | étude pour déterminer si les conditions peuvent devenir entièrement binaires |
| Ponctuation finale de note | adaptateur legacy | score `footnote_form`, probablement `review_only` jusqu’à validation |
| Entrée/sortie de bibliographie | adaptateur à état reproduisant les préfixes et styles bruts | score `bibliography_structure` fondé sur sémantique et contexte |
| Promotion bibliographique | adaptateur legacy | décision issue du même score de section |
| Ponctuation bibliographique | adaptateur legacy | score `bibliography_form`, puis décision éditoriale |
| Promotions structurelles non scorées | adaptateurs par règle | rattachement à une famille calibrée |
| Épigraphe | adaptateur legacy | famille dédiée ou `review_only` |
| Citation longue | adaptateur legacy | score `quote_structure` |
| Fusion de poésie encadrée de blancs | adaptateur legacy | intégrer au score `poetry`, avec action de fusion explicitement proposée |

Un adaptateur legacy produit un résultat conforme au nouveau modèle et une
issue reproduisant le comportement actuel. Il est identifié dans la trace et
ne constitue pas une validation de la règle.

---

## 14. Anomalies caractérisées à préserver

La migration à comportement constant contient des tests explicites pour les
faits suivants :

1. `Sources de…` ouvre une section bibliographique.
2. Un heading portant seulement `style_id="Heading 1"` ne ferme pas cette
   section dans le normaliseur bibliographique.
3. Un DOI de note sans point reçoit un point final.
4. `art. cit.` initial reste en minuscule.
5. `R-AN-003` peut être émis sans `R-AN-002`.
6. Une protection explicite n’empêche pas aujourd’hui une promotion
   structurelle.
7. `bibliography_item` est traité par son propre normaliseur tant qu’il n’est
   pas explicitement protégé.
8. Le mode `deterministic` conserve front matter et promotion par style source.
9. Certains chemins structurels diagnostiques mutent des attributs.

Les adaptateurs portent un code de compatibilité pour rendre ces anomalies
visibles. Leur correction exige une passe séparée et une décision éditoriale.

---

## 15. Traçabilité et invariants

### 15.1 Invariants obligatoires

- `rule_id` stable et présent ;
- `target_ref` ou liste de cibles explicite ;
- texte/structure/style avant et après ;
- offsets dans la version du texte sur laquelle la règle s’est exécutée ;
- ordre global d’application ;
- stylage traçable sans changement de texte brut ;
- listes des blocs créés, supprimés, conservés et fusionnés ;
- diagnostic distinct d’une mutation ;
- snapshot du statut, des seuils et des protections ;
- second passage idempotent lorsque l’action est canonique ;
- restitution Word fondée sur les transformations journalisées, sans nouvelle
  décision éditoriale ;
- sémantique structurelle écrite dans le pivot avant export.

### 15.2 Ordonnancement

Le moteur reçoit une séquence explicite et stable. Une règle ne redécouvre pas
silencieusement les offsets dans un texte déjà transformé sans que la version
de référence soit connue. Les règles couplées de siècle et numéro conservent
leur transformation textuelle puis leur transformation de style.

### 15.3 Diagnostics et mutations

Une issue `review` ne peut muter ni texte, ni style, ni structure. Les mutations
d’attributs actuellement associées à certains diagnostics structurels ne sont
préservées que dans l’adaptateur legacy, avec un drapeau
`legacy_diagnostic_side_effect`. Elles doivent disparaître dans une passe
corrective ultérieure.

---

## 16. Plan de migration fichier par fichier

Ce plan décrit des passes futures ; aucun de ces fichiers n’est modifié pendant
la présente passe.

| Fichier cible proposé | Rôle futur | Mode de migration |
|---|---|---|
| `rules/model.py` | enums et dataclasses communes | ajout pur, tests unitaires |
| `rules/protocols.py` | protocoles d’évaluation/exécution | ajout pur |
| `rules/registry.py` | descripteurs et validation | métadonnées seulement |
| `rules/engine.py` | décision `apply/review/ignore` | d’abord en mode shadow |
| `rules/thresholds.py` | politiques familiales et interpolation | reproduire exactement titre/poésie |
| `rules/protections.py` | résolution versionnée des protections | commencer en mode legacy |
| `rules/compatibility.py` | traduction profils, seuils et mode legacy | aucun paramètre IA |
| `rules/adapters/orthotypography.py` | enveloppe des `TypoRule` actuelles | conserver ordre, offsets et liste blanche |
| `rules/adapters/footnotes.py` | enveloppe du normaliseur de notes | préserver toutes les branches |
| `rules/adapters/bibliography.py` | état de section et règles locales | préserver anomalies de frontière |
| `rules/adapters/structure.py` | décisions et mutations structurelles actuelles | préserver profils et effets de bord caractérisés |
| `services/orthotypo_service.py` | délégation progressive | une règle à la fois |
| `services/footnote_normalizer.py` | délégation progressive | après orthotypographie |
| `services/bibliography_normalizer.py` | délégation progressive | après notes |
| `services/structure_service.py` | délégation et retrait progressif des branches concurrentes | dernier service migré |
| `pipeline/step1.py` | création de la configuration non IA et collecte du journal | après validation shadow |
| configuration non IA | sérialisation du niveau et lecture legacy | sans toucher aux paramètres IA |
| UI non IA | futur curseur unique | seulement après stabilisation du contrat |

Les modèles de production existants `Transformation` et `Diagnostic` restent
les objets de sortie pendant la première migration. Le nouveau journal les
alimente avant toute éventuelle évolution de schéma.

---

## 17. Étapes d’implémentation proposées

1. **Socle pur** : introduire types, registre et validations sans branchement au
   pipeline.
2. **Tests du moteur** : couvrir toutes les combinaisons nature/action/statut,
   protections et seuils.
3. **Mode shadow** : exécuter le moteur sans mutation, comparer ses décisions
   aux sorties legacy.
4. **Orthotypographie** : migrer d’abord les six règles actives, puis les règles
   `review_only`, en conservant l’ordre.
5. **Notes** : brancher l’adaptateur complet avant toute tentative de score.
6. **Bibliographie** : migrer l’automate de section et les règles locales sans
   corriger ses frontières.
7. **Structure** : intégrer les scores titre/poésie, puis envelopper les
   transformations non scorées.
8. **Compatibilité pipeline/configuration** : traduire profils, seuils et mode
   historique ; sérialiser le nouveau niveau.
9. **Activation par famille** : exécuter le nouveau moteur comme autorité après
   égalité constatée en shadow.
10. **Dépréciation** : retirer progressivement `auto`,
    `auto_apply_diagnostics` et les anciens profils seulement après période de
    compatibilité.
11. **Passes éditoriales ultérieures** : décider les statuts, calibrer les
    nouvelles familles et harmoniser les protections.

Chaque étape possède un mécanisme de repli par famille. Il est interdit
d’exécuter simultanément l’ancien et le nouveau mutateur sur le même contenu.

---

## 18. Tests à maintenir ou ajouter

### 18.0 Matrice par étape

| Étape | Tests bloquants avant passage à l’étape suivante |
|---|---|
| Socle pur | enums, dataclasses, validation du registre, sérialisation |
| Moteur | matrice des trois issues, actions diagnostiques, protections |
| Shadow | égalité des décisions observables avec chaque service legacy |
| Orthotypographie | corpus par règle, ordre, offsets, styles seuls, idempotence |
| Notes | matrice début/fin, diagnostics d’appels, protections héritées |
| Bibliographie | frontières, promotions, style, règles locales, anomalies |
| Structure | profils, vetos, fusions, IDs, mutations diagnostiques legacy |
| Pipeline/configuration | anciennes configurations, rapports et ordre des modules |
| Dépréciation | absence d’appel aux chemins retirés et compatibilité documentée |

### 18.1 Socle et registre

- unicité et stabilité des `rule_id` ;
- cohérence nature/action/statut/score ;
- présence des sources et des tests associés ;
- sérialisation sans proxy ni objet non JSON.

### 18.2 Moteur

- matrice déterministe/heuristique × active/review_only/disabled ;
- action déterministe de diagnostic ;
- veto prioritaire ;
- curseur sans effet sur les règles déterministes ;
- règle `review_only` jamais appliquée, même au niveau maximal ;
- journal complet et ordre stable.

### 18.3 Seuils et compatibilité

- ancres 0/50/100 exactement égales aux profils actuels ;
- interpolation reproductible ;
- bornes et incohérences ;
- seuils explicites legacy ;
- profil exploratoire reproduit sans booléen postérieur ;
- mode `deterministic` legacy et transformations résiduelles ;
- ancienne configuration relisible ;
- paramètres IA ignorés par le traducteur.

### 18.4 Familles

Conserver intégralement :

- `test_orthotypo_deployment_characterization.py` ;
- `test_footnote_characterization_matrix.py` ;
- `test_bibliography_characterization_boundaries.py` ;
- `test_structure_characterization_modes_and_protection.py` ;
- `test_protection_asymmetry_characterization.py` ;
- les corpus normatifs, tests d’offsets, de styles, de scoring, de vetos,
  d’idempotence et de pipeline existants.

Ajouter à chaque migration :

- comparaison shadow legacy/nouveau ;
- texte et signature stylistique ;
- transformations et diagnostics ordonnés ;
- cibles et offsets ;
- blocs créés/supprimés/fusionnés ;
- protections et asymétries legacy ;
- second passage ;
- pivot JSON et rendu Word lorsque la trace est rendue visible.

### 18.5 Futures passes correctives

Créer de nouveaux tests, sans modifier les tests de caractérisation historique,
pour :

- protections structurelles transversales ;
- frontières bibliographiques canoniques ;
- absence de mutation lors d’une issue `review` ;
- scores notes/bibliographie calibrés ;
- changement de statut explicitement validé.

---

## 19. Risques et mesures de repli

| Risque | Mesure |
|---|---|
| Divergence registre/logique | validation automatique des IDs et mode shadow |
| Changement d’ordre des règles | séquence explicite et tests d’ordre |
| Double application | un seul exécuteur autoritaire par famille |
| Décalage d’offsets | version/signature du texte source dans chaque décision |
| Perte des stylages seuls | signature texte + style |
| Dérive des scores | version des formules et ancres par famille |
| Fausse comparabilité des scores | seuils distincts par famille |
| Activation accidentelle d’une règle | statut publié non modifiable par le curseur |
| Correction involontaire d’une anomalie | adaptateurs et tests de caractérisation |
| Modification des protections | résolveur versionné en mode legacy initial |
| Perte d’identifiants lors d’une fusion | action structurelle avec IDs complets |
| Configuration contradictoire | validation native stricte, traducteur legacy explicite |
| Rupture du rendu Word | tests des transformations et surlignages existants |

Le repli consiste à désactiver le nouveau chemin pour une famille entière et à
revenir à son adaptateur legacy. Il ne consiste jamais à mélanger deux moteurs
de mutation dans une même exécution.

---

## 20. Décisions humaines encore requises

Avant toute activation ou correction nouvelle, les PURH doivent valider :

1. les sources normatives admises pour une règle automatique ;
2. le statut des guillemets, espaces, ligatures et ponctuations non inscrits
   dans la liste blanche actuelle ;
3. les contextes techniques constituant des vetos binaires complets ;
4. la majuscule et la ponctuation finale des notes ;
5. le traitement des abréviations latines selon le modèle bibliographique ;
6. les frontières et le modèle canonique des sections bibliographiques ;
7. la ponctuation finale des entrées bibliographiques ;
8. l’autorité accordée aux styles Word de titre ;
9. le statut de l’épigraphe, de la citation longue et des promotions
   structurelles non scorées ;
10. l’automatisation des fusions poétiques ;
11. la politique cible uniforme des protections ;
12. la calibration et le libellé des nouvelles familles de score ;
13. le devenir du tiret d’incise.

---

## 21. Décision architecturale de synthèse

La cible est un moteur commun, petit et indépendant des interfaces, auquel les
règles remettent des constats ou propositions sans modifier le document. Le
registre décrit les règles sans dupliquer leur logique. Le statut de
déploiement reste une décision éditoriale versionnée. Les heuristiques utilisent
des seuils propres à leur famille et un unique niveau global traduit par une
politique explicite. L’exécuteur matérialise ensuite l’action et conserve la
traçabilité existante.

La migration commence par des adaptateurs et un mode shadow. Elle ne change ni
la liste blanche, ni les seuils, ni les protections, ni les anomalies
caractérisées. Les corrections éditoriales et l’harmonisation des protections
restent des passes ultérieures distinctes.
