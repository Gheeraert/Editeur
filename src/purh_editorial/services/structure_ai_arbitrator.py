from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from purh_editorial.model import Diagnostic, Document, Evidence, InlineSpan, Transformation
from purh_editorial.model.semantics import BlockSemantics, write_block_semantics
from purh_editorial.utils import make_id


def _merge_verse_inlines(blocks: list) -> list[InlineSpan]:
    merged: list[InlineSpan] = []
    for index, block in enumerate(blocks):
        if block.inlines:
            merged.extend(block.inlines)
        else:
            merged.append(InlineSpan(text=block.text.strip()))
        if index < len(blocks) - 1:
            merged.append(InlineSpan(text="", kind="line_break"))
    return merged

# ── Prompt système PURH — contexte éditorial riche ───────────────────────────

_PURH_STRUCTURE_SYSTEM_PROMPT = """\
Tu es un expert en édition scientifique française, spécialisé dans la préparation \
éditoriale des manuscrits académiques pour les Presses universitaires de Rouen et \
du Havre (PURH).

CONTEXTE ÉDITORIAL PURH
Les manuscrits PURH sont des ouvrages en SHS (sciences humaines et sociales) : \
histoire, littérature, linguistique, arts. La chaîne éditoriale utilise les styles \
Métopes (XML single-source → TEI → DOCX/PDF/Web).
Styles structurels cibles : Titre1, Titre2, Titre3, Normal, \
TEIparagraphconsecutive, TEIquote, TEIbiblreference.

ZONES GRISES — TU ARBITRES CES CAS UNIQUEMENT :

1. TITRE (candidat) — paragraphe court sans ponctuation finale
   • Indices positifs : < 80 caractères, pas de point final, pas de virgule \
interne, texte en gras ou petites caps dans le manuscrit auteur, entouré de \
longs paragraphes développés.
   • Pièges : noms d'auteurs en italique (2-3 mots), numéros romains seuls \
(I, II, III), initiales de section (A., B.), items de liste sans marqueur visible.

2. POÉSIE / VERS (candidat)
   • Indices positifs : suite de lignes très courtes (< 60 chars), majuscule \
initiale à chaque vers, espaces entre strophes, enjambements, rhythme.
   • Pièges : listes à puces sans marqueur, entrées bibliographiques courtes, \
glossaires.

3. LISTE (items non marqués)
   • Items courts de longueur similaire, structure répétitive, parfois introduits \
par un tiret ou un numéro.
   • Se distingue de la poésie : structure mécanique, pas de souffle lyrique.
   • Se distingue des titres : plusieurs items consécutifs de même niveau.

4. RÉFÉRENCE ISOLÉE (bibliographie hors section dédiée)
   • Format typique : NOM Prénom, «Titre», Lieu : Éditeur, année, p. XX–XX.
   • Contient chiffres, virgules, une année (4 chiffres).
   • Souvent après une citation ou une note de bas de page.

5. CITATION (bloc extrait)
   • Paragraphe en retrait gauche ou texte encadré par «  ».
   • Peut s'étaler sur plusieurs fragments si l'auteur a coupé.

RÈGLE D'ARBITRAGE
- confidence ≥ 0.85 → classification exploitable pour revue humaine ou traitement déterministe ultérieur
- 0.70 ≤ confidence < 0.85 → diagnostic à soumettre à l'éditrice
- confidence < 0.70 → incertain, conserver le status quo

Tu ne modifies JAMAIS le texte et tu ne promets JAMAIS une transformation directe. Tu réponds UNIQUEMENT en JSON strict.\
"""

ALLOWED_CLASSIFICATIONS = {
    "heading",
    "poetry_quote",
    "paragraph",
    "reference",
    "list_item",
    "caption",
    "bibliography",
    "isolated_reference",
    "uncertain",
}

ALLOWED_RECOMMENDED_ACTIONS = {"transform", "diagnostic", "ignore"}
ALLOWED_AI_AGGRESSIVENESS = {"conservative", "balanced", "aggressive"}

_ARBITRATION_RULE_ID = "R-STRUCT-AI-LOCAL-001"
_ARBITRATION_CATEGORY = "structure_ai_arbitration"
_CLUSTER_RULE_ID = "R-STRUCT-CLUSTER-001"
_CLUSTER_CATEGORY = "paragraph_cluster_candidate"
_APPLY_RULE_ID = "R-STRUCT-AI-APPLY-001"
_APPLY_CATEGORY = "structure_ai_apply"

# Rule IDs that are eligible for individual block arbitration.
_ARBITRATED_RULE_IDS = {"R-STRUCT-HEADING-001", "R-CI-POETRY-001", "structure.bibliography.heuristic"}

# Short paragraph cluster parameters.
_CLUSTER_MAX_LINE_LEN = 80
_CLUSTER_MIN_SIZE = 3
_CLUSTER_MAX_SIZE = 20


@dataclass(slots=True)
class AiArbitrationResult:
    classification: str
    confidence: float
    reason: str
    recommended_action: str


@dataclass(slots=True)
class AiArbitrationCandidate:
    candidate_type: str
    target_refs: list[str] = field(default_factory=list)
    excerpt: str = ""
    context_before: str = ""
    context_after: str = ""
    score: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)
    decision: str = "diagnostic"
    veto_reasons: list[str] = field(default_factory=list)
    ai_candidate: bool = False


@dataclass(slots=True)
class StructureAiArbitrationSettings:
    confidence_threshold: float = 0.85
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.0
    max_tokens: int = 220


def normalize_ai_aggressiveness(level: str | None) -> str:
    if not level:
        return "conservative"
    value = str(level).strip().lower()
    if value in ALLOWED_AI_AGGRESSIVENESS:
        return value
    return "conservative"


def settings_for_ai_aggressiveness(
    level: str | None,
    *,
    base_model: str = "llama-3.3-70b-versatile",
    base_max_structure_ai_calls: int = 6,
) -> tuple[StructureAiArbitrationSettings, int]:
    normalized = normalize_ai_aggressiveness(level)
    base_calls = max(1, int(base_max_structure_ai_calls))
    if normalized == "balanced":
        return (
            StructureAiArbitrationSettings(
                confidence_threshold=0.85,
                model=base_model,
            ),
            base_calls,
        )
    if normalized == "aggressive":
        return (
            StructureAiArbitrationSettings(
                confidence_threshold=0.75,
                model=base_model,
            ),
            base_calls,
        )
    # conservative
    return (
        StructureAiArbitrationSettings(
            confidence_threshold=0.90,
            model=base_model,
        ),
        max(1, base_calls // 2),
    )


class StructureAiProvider(Protocol):
    def complete(self, prompt: str) -> str:
        ...


class GroqStructureAiProvider:
    """Provider OpenAI-compatible (Groq) pour l'arbitrage structurel."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 20,
        temperature: float = 0.0,
        max_tokens: int = 220,
        system_prompt: str = _PURH_STRUCTURE_SYSTEM_PROMPT,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "purh-editorial/structure-ai",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Groq HTTP {exc.code}: {detail[:200]}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Groq error: {exc}") from exc

        return (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )


class AnthropicStructureAiProvider:
    """Provider natif Anthropic Messages API pour l'arbitrage structurel.

    Utilise directement l'API Anthropic (pas OpenAI-compatible).
    Recommandé pour la qualité du français et la précision classificatoire.
    Modèle par défaut : claude-haiku-4-5-20251001 (rapport qualité/prix optimal).
    """

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"
    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 20,
        max_tokens: int = 220,
        system_prompt: str = _PURH_STRUCTURE_SYSTEM_PROMPT,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}/messages",
            data=data,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "purh-editorial/structure-ai",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic HTTP {exc.code}: {detail[:200]}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Anthropic error: {exc}") from exc

        content_blocks = body.get("content", [])
        if not content_blocks:
            return ""
        return str(content_blocks[0].get("text", "")).strip()


def build_structure_ai_prompt(candidate: AiArbitrationCandidate) -> str:
    evidence_json = json.dumps(candidate.evidence, ensure_ascii=False)
    target_refs = ", ".join(candidate.target_refs)
    candidate_label = {
        "heading": "candidat TITRE",
        "poetry": "candidat POÉSIE/VERS",
        "bibliography": "candidat RÉFÉRENCE BIBLIOGRAPHIQUE ISOLÉE",
    }.get(candidate.candidate_type, f"candidat {candidate.candidate_type.upper()}")

    return (
        f"Arbitrage structurel — {candidate_label}\n\n"
        f"Identifiant(s) cible : {target_refs}\n"
        f"Score heuristique : {candidate.score:.2f} "
        f"(décision heuristique actuelle : {candidate.decision})\n\n"
        f"CONTEXTE AVANT :\n{candidate.context_before or '(début de document)'}\n\n"
        f"PASSAGE À CLASSIFIER :\n{candidate.excerpt}\n\n"
        f"CONTEXTE APRÈS :\n{candidate.context_after or '(fin de document)'}\n\n"
        f"Indices heuristiques : {evidence_json}\n\n"
        "Réponds UNIQUEMENT avec ce JSON strict :\n"
        '{"classification":"heading|poetry_quote|list_item|isolated_reference|'
        'paragraph|reference|caption|bibliography|uncertain",'
        '"confidence":0.0,"reason":"explication courte",'
        '"recommended_action":"transform|diagnostic|ignore"}'
    )


def parse_structure_ai_json(raw: str) -> AiArbitrationResult:
    text = raw.strip()
    if not text:
        raise ValueError("empty_response")
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("invalid_json") from exc
        data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("non_object_json")

    classification = str(data.get("classification", "")).strip()
    recommended_action = str(data.get("recommended_action", "")).strip()
    reason = str(data.get("reason", "")).strip()
    confidence_raw = data.get("confidence")

    if classification not in ALLOWED_CLASSIFICATIONS:
        raise ValueError("unknown_classification")
    if recommended_action not in ALLOWED_RECOMMENDED_ACTIONS:
        raise ValueError("unknown_recommended_action")
    if not isinstance(confidence_raw, (float, int)):
        raise ValueError("invalid_confidence_type")

    confidence = float(confidence_raw)
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence_out_of_range")

    return AiArbitrationResult(
        classification=classification,
        confidence=confidence,
        reason=reason,
        recommended_action=recommended_action,
    )


class StructureAiArbitrator:
    module_name = "structure_ai_arbitration"

    def __init__(
        self,
        *,
        provider: StructureAiProvider | None = None,
        settings: StructureAiArbitrationSettings | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings or StructureAiArbitrationSettings()

    def arbitrate_from_diagnostics(
        self,
        *,
        document: Document,
        diagnostics: list[Diagnostic],
        enable_ai: bool,
        max_calls: int | None = None,
    ) -> tuple[list[Diagnostic], list[str], int]:
        """Arbitre les diagnostics de zones grises individuelles (titres, poésie, références)."""
        if not enable_ai:
            return [], [], 0
        if self.provider is None:
            return [], ["Structure AI arbitration skipped: no provider configured."], 0

        results: list[Diagnostic] = []
        warnings: list[str] = []
        calls = 0
        cap = max_calls if max_calls is None else max(0, int(max_calls))

        for diagnostic in diagnostics:
            if cap is not None and calls >= cap:
                break
            candidate = self._candidate_from_diagnostic(document=document, diagnostic=diagnostic)
            if candidate is None:
                continue
            if not candidate.ai_candidate:
                continue
            if candidate.veto_reasons:
                continue

            prompt = build_structure_ai_prompt(candidate)
            calls += 1
            try:
                raw = self.provider.complete(prompt)
                parsed = parse_structure_ai_json(raw)
            except Exception as exc:  # noqa: BLE001
                results.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="warning",
                        category=_ARBITRATION_CATEGORY,
                        message="Arbitrage IA local non exploitable (réponse invalide).",
                        target_ref=candidate.target_refs[0] if candidate.target_refs else diagnostic.target_ref,
                        rule_id=_ARBITRATION_RULE_ID,
                        evidence=Evidence(excerpt=candidate.excerpt[:200]),
                        attributes={
                            "error": str(exc),
                            "candidate_type": candidate.candidate_type,
                        },
                    )
                )
                continue

            if parsed.confidence >= self.settings.confidence_threshold and parsed.classification != "uncertain":
                message = "Arbitrage IA local: classification exploitable pour revue humaine."
            else:
                message = "Arbitrage IA local incertain: conserver un diagnostic prudent."

            results.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="info",
                    category=_ARBITRATION_CATEGORY,
                    message=message,
                    target_ref=candidate.target_refs[0] if candidate.target_refs else diagnostic.target_ref,
                    rule_id=_ARBITRATION_RULE_ID,
                    evidence=Evidence(excerpt=candidate.excerpt[:200]),
                    attributes={
                        "candidate_type": candidate.candidate_type,
                        "classification": parsed.classification,
                        "confidence": parsed.confidence,
                        "reason": parsed.reason,
                        "recommended_action": parsed.recommended_action,
                        "score": candidate.score,
                        "veto_reasons": candidate.veto_reasons,
                        "ai_candidate": candidate.ai_candidate,
                    },
                )
            )

        return results, warnings, calls

    def analyze_short_paragraph_clusters(
        self,
        *,
        document: Document,
        enable_ai: bool,
        max_calls: int | None = None,
    ) -> tuple[list[Diagnostic], list[str], int]:
        """Identifie les séquences de paragraphes courts et demande à l'IA de les classifier.

        Cible les zones grises non couvertes par les heuristiques individuelles :
        listes sans marqueur, séquences poétiques oubliées, références isolées
        consécutives, suites de sous-titres non formatés.
        """
        if not enable_ai:
            return [], [], 0
        if self.provider is None:
            return [], ["Cluster AI analysis skipped: no provider configured."], 0

        clusters = _find_short_paragraph_clusters(document)
        if not clusters:
            return [], [], 0

        results: list[Diagnostic] = []
        warnings: list[str] = []
        calls = 0
        cap = max(0, int(max_calls)) if max_calls is not None else None

        for cluster in clusters:
            if cap is not None and calls >= cap:
                break
            prompt = _build_cluster_prompt(cluster, document)
            calls += 1
            try:
                raw = self.provider.complete(prompt)
                parsed = parse_structure_ai_json(raw)
            except Exception as exc:  # noqa: BLE001
                results.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="warning",
                        category=_CLUSTER_CATEGORY,
                        message="Analyse IA du cluster non exploitable (réponse invalide).",
                        target_ref=cluster["block_ids"][0],
                        rule_id=_CLUSTER_RULE_ID,
                        evidence=Evidence(excerpt=cluster["excerpt"]),
                        attributes={"error": str(exc), "cluster_size": len(cluster["block_ids"])},
                    )
                )
                continue

            size = len(cluster["block_ids"])
            if parsed.confidence >= self.settings.confidence_threshold and parsed.classification != "uncertain":
                message = (
                    f"Cluster de {size} paragraphes courts : IA suggère «{parsed.classification}» "
                    f"(confiance {parsed.confidence:.0%})."
                )
            else:
                message = (
                    f"Cluster de {size} paragraphes courts : classification incertaine "
                    f"(IA hésite, confiance {parsed.confidence:.0%})."
                )

            results.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="info",
                    category=_CLUSTER_CATEGORY,
                    message=message,
                    target_ref=cluster["block_ids"][0],
                    rule_id=_CLUSTER_RULE_ID,
                    evidence=Evidence(excerpt=cluster["excerpt"]),
                    attributes={
                        "classification": parsed.classification,
                        "confidence": parsed.confidence,
                        "reason": parsed.reason,
                        "recommended_action": parsed.recommended_action,
                        "cluster_size": size,
                        "block_ids": cluster["block_ids"],
                    },
                )
            )

        return results, warnings, calls

    def apply_cluster_transformations(
        self,
        *,
        document: Document,
        diagnostics: list[Diagnostic],
        enable_ai_transform: bool,
        confidence_threshold: float | None = None,
    ) -> tuple[list[Transformation], list[Diagnostic], dict[str, Any]]:
        """Apply a minimal set of structural AI actions from cluster diagnostics.

        First pass scope:
        - apply only poetry_quote clusters when action=transform and confidence >= threshold
        - refuse list_item transformations with a traceable diagnostic
        """
        summary: dict[str, Any] = {
            "candidates": 0,
            "applied": 0,
            "refused": 0,
            "refusal_reasons": {},
        }
        if not enable_ai_transform:
            return [], [], summary

        threshold = (
            self.settings.confidence_threshold
            if confidence_threshold is None
            else float(confidence_threshold)
        )
        transformations: list[Transformation] = []
        out_diags: list[Diagnostic] = []
        blocks_by_id = {block.block_id: block for block in document.blocks}

        def _refuse(target_ref: str, message: str, reason_code: str, attrs: dict[str, Any]) -> None:
            summary["refused"] += 1
            reasons = summary["refusal_reasons"]
            reasons[reason_code] = int(reasons.get(reason_code, 0)) + 1
            out_diags.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="info",
                    category=_APPLY_CATEGORY,
                    message=message,
                    target_ref=target_ref,
                    rule_id=_APPLY_RULE_ID,
                    evidence=Evidence(excerpt=str(attrs.get("excerpt", ""))[:240]),
                    attributes={
                        "status": "refused",
                        "reason_code": reason_code,
                        **attrs,
                    },
                )
            )

        for diagnostic in diagnostics:
            if diagnostic.rule_id != _CLUSTER_RULE_ID or diagnostic.category != _CLUSTER_CATEGORY:
                continue
            attrs = diagnostic.attributes or {}
            classification = str(attrs.get("classification", "")).strip()
            recommended_action = str(attrs.get("recommended_action", "")).strip()
            reason = str(attrs.get("reason", "")).strip()
            try:
                confidence = float(attrs.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            block_ids_raw = attrs.get("block_ids", [])
            block_ids = [str(ref) for ref in block_ids_raw if ref] if isinstance(block_ids_raw, list) else []
            target_ref = block_ids[0] if block_ids else (diagnostic.target_ref or "")
            cluster_attrs = {
                "classification": classification,
                "recommended_action": recommended_action,
                "confidence": confidence,
                "confidence_threshold": threshold,
                "reason": reason,
                "block_ids": block_ids,
                "excerpt": attrs.get("excerpt", diagnostic.evidence.excerpt if diagnostic.evidence else ""),
            }

            if classification not in {"poetry_quote", "list_item"}:
                continue
            summary["candidates"] += 1

            if classification == "list_item":
                _refuse(
                    target_ref,
                    "transformation refusée : type liste non encore supporté par cette passe",
                    "list_not_supported",
                    cluster_attrs,
                )
                continue

            if recommended_action != "transform":
                _refuse(
                    target_ref,
                    "Transformation refusée : action IA non transformante.",
                    "action_not_transform",
                    cluster_attrs,
                )
                continue
            if confidence < threshold:
                _refuse(
                    target_ref,
                    "Transformation refusée : confiance IA sous le seuil configuré.",
                    "confidence_below_threshold",
                    cluster_attrs,
                )
                continue
            if not block_ids:
                _refuse(
                    target_ref,
                    "Transformation refusée : cluster sans cibles exploitables.",
                    "missing_targets",
                    cluster_attrs,
                )
                continue

            blocked_reason: str | None = None
            for block_id in block_ids:
                block = blocks_by_id.get(block_id)
                if block is None:
                    blocked_reason = "missing_block"
                    break
                if block.block_type != "paragraph":
                    blocked_reason = "block_type_not_supported"
                    break
                protected_zone = str(block.attributes.get("protected_zone", "")).strip().lower()
                if protected_zone and protected_zone != "poetry":
                    blocked_reason = "protected_zone_veto"
                    break

            if blocked_reason is not None:
                _refuse(
                    target_ref,
                    "Transformation refusée : veto ou contraintes structurelles.",
                    blocked_reason,
                    cluster_attrs,
                )
                continue

            source_blocks = [blocks_by_id[bid] for bid in block_ids if bid in blocks_by_id]
            first_block = source_blocks[0]
            before = first_block.block_type
            lines = [b.text.strip() for b in source_blocks if b.text.strip()]
            first_block.text = "\n".join(lines)
            first_block.inlines = _merge_verse_inlines(source_blocks)
            first_block.block_type = "lineated_block"
            first_block.attributes["alignment"] = "left"
            first_block.attributes["merged_from"] = block_ids
            first_block.attributes["protected_zone"] = "poetry"
            first_block.attributes["highlight_color"] = "ai_structure"
            first_block.attributes["ai_structure_confidence"] = confidence
            first_block.attributes["ai_structure_reason"] = reason
            first_block.attributes["ai_structure_source_rule"] = _CLUSTER_RULE_ID
            write_block_semantics(
                first_block,
                BlockSemantics(
                    role="lineated_block",
                    layout_kind="lineated_block",
                    lineation="lineated",
                    genre_hint="poetry",
                    genre_confidence=confidence,
                    genre_source="ai",
                    lines=lines,
                ),
            )
            consumed_ids = {bid for bid in block_ids[1:] if bid in blocks_by_id}
            if consumed_ids:
                document.blocks = [b for b in document.blocks if b.block_id not in consumed_ids]
                blocks_by_id = {b.block_id: b for b in document.blocks}
            applied_block_ids = [first_block.block_id]
            transformations.append(
                Transformation(
                    transformation_id=make_id("tr"),
                    module=self.module_name,
                    target_ref=first_block.block_id,
                    operation="ai_structure_transform",
                    before=before,
                    after="lineated_block",
                    rule_id=_APPLY_RULE_ID,
                    applied=True,
                    attributes={
                        "classification": classification,
                        "recommended_action": recommended_action,
                        "confidence": confidence,
                        "confidence_threshold": threshold,
                        "merged_from": block_ids,
                        "reason": reason,
                        "source_rule_id": _CLUSTER_RULE_ID,
                    },
                )
            )

            summary["applied"] += 1
            out_diags.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="info",
                    category=_APPLY_CATEGORY,
                    message="Transformation IA structurelle appliquée : cluster versifié.",
                    target_ref=target_ref,
                    rule_id=_APPLY_RULE_ID,
                    evidence=Evidence(excerpt=str(cluster_attrs["excerpt"])[:240]),
                    attributes={
                        "status": "applied",
                        "classification": classification,
                        "recommended_action": recommended_action,
                        "confidence": confidence,
                        "confidence_threshold": threshold,
                        "block_ids": applied_block_ids,
                        "reason": reason,
                    },
                )
            )

        return transformations, out_diags, summary

    @staticmethod
    def _candidate_from_diagnostic(
        *,
        document: Document,
        diagnostic: Diagnostic,
    ) -> AiArbitrationCandidate | None:
        if diagnostic.rule_id not in _ARBITRATED_RULE_IDS:
            return None

        attrs = diagnostic.attributes or {}
        target_refs = attrs.get("target_refs")
        if not isinstance(target_refs, list) or not target_refs:
            target_refs = [diagnostic.target_ref] if diagnostic.target_ref else []
        target_refs = [str(ref) for ref in target_refs if ref]

        score = float(attrs.get("score", 0.0))
        decision = str(attrs.get("decision", "diagnostic"))
        evidence = attrs.get("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}
        veto_reasons = attrs.get("veto_reasons", [])
        if not isinstance(veto_reasons, list):
            veto_reasons = []
        ai_candidate = bool(attrs.get("ai_candidate", False))

        # Bibliography heuristic: always treat as AI candidate (no score system)
        if diagnostic.rule_id == "structure.bibliography.heuristic":
            ai_candidate = True
            score = score or 0.5

        excerpt = ""
        if isinstance(evidence.get("excerpt"), str):
            excerpt = evidence["excerpt"]
        if not excerpt and diagnostic.evidence and diagnostic.evidence.excerpt:
            excerpt = diagnostic.evidence.excerpt

        context_before, context_after = _local_context(
            document=document,
            target_ref=target_refs[0] if target_refs else "",
        )

        if diagnostic.rule_id == "R-STRUCT-HEADING-001":
            candidate_type = "heading"
        elif diagnostic.rule_id == "R-CI-POETRY-001":
            candidate_type = "poetry"
        else:
            candidate_type = "bibliography"

        return AiArbitrationCandidate(
            candidate_type=candidate_type,
            target_refs=target_refs,
            excerpt=excerpt,
            context_before=context_before,
            context_after=context_after,
            score=score,
            evidence=evidence,
            decision=decision,
            veto_reasons=[str(reason) for reason in veto_reasons],
            ai_candidate=ai_candidate,
        )


# ── Contexte local — 3 paragraphes avant/après ───────────────────────────────

def _local_context(*, document: Document, target_ref: str, window: int = 3) -> tuple[str, str]:
    """Retourne jusqu'à `window` paragraphes avant et après target_ref."""
    if not target_ref:
        return "", ""
    for index, block in enumerate(document.blocks):
        if block.block_id != target_ref:
            continue
        before_blocks = document.blocks[max(0, index - window):index]
        after_blocks = document.blocks[index + 1:index + 1 + window]
        before = " / ".join(b.text.strip()[:300] for b in before_blocks if b.text.strip())
        after = " / ".join(b.text.strip()[:300] for b in after_blocks if b.text.strip())
        return before[:700], after[:700]
    return "", ""


# ── Détection de clusters de paragraphes courts ───────────────────────────────

def _find_short_paragraph_clusters(document: Document) -> list[dict]:
    """Trouve les séquences de paragraphes courts consécutifs (≥3, ≤20)."""
    clusters: list[dict] = []
    current: list = []

    for block in document.blocks:
        text = block.text.strip()
        is_short = (
            block.block_type == "paragraph"
            and 5 < len(text) <= _CLUSTER_MAX_LINE_LEN
        )
        if is_short:
            current.append(block)
        else:
            if len(current) >= _CLUSTER_MIN_SIZE:
                chunk = current[:_CLUSTER_MAX_SIZE]
                clusters.append({
                    "block_ids": [b.block_id for b in chunk],
                    "lines": [b.text.strip() for b in chunk],
                    "excerpt": "\n".join(b.text.strip() for b in chunk[:8]),
                })
            current = []

    if len(current) >= _CLUSTER_MIN_SIZE:
        chunk = current[:_CLUSTER_MAX_SIZE]
        clusters.append({
            "block_ids": [b.block_id for b in chunk],
            "lines": [b.text.strip() for b in chunk],
            "excerpt": "\n".join(b.text.strip() for b in chunk[:8]),
        })

    return clusters


def _build_cluster_prompt(cluster: dict, document: Document) -> str:
    """Construit le prompt pour l'analyse d'un cluster de paragraphes courts."""
    block_ids = cluster["block_ids"]
    lines = cluster["lines"]
    size = len(lines)

    first_ref = block_ids[0]
    last_ref = block_ids[-1]
    context_before, _ = _local_context(document=document, target_ref=first_ref, window=2)
    _, context_after = _local_context(document=document, target_ref=last_ref, window=2)

    cluster_text = "\n".join(f"  [{i + 1}] {line}" for i, line in enumerate(lines))

    return (
        f"Analyse ce cluster de {size} paragraphes consécutifs courts "
        f"(chacun ≤ {_CLUSTER_MAX_LINE_LEN} caractères).\n\n"
        f"CONTEXTE AVANT LE CLUSTER :\n{context_before or '(début de document)'}\n\n"
        f"CLUSTER À CLASSIFIER :\n{cluster_text}\n\n"
        f"CONTEXTE APRÈS LE CLUSTER :\n{context_after or '(fin de document)'}\n\n"
        "Ce cluster est-il :\n"
        "  • De la POÉSIE (poetry_quote) : vers courts, majuscule initiale, souffle lyrique\n"
        "  • Une LISTE (list_item) : items parallèles, structure mécanique répétitive\n"
        "  • Des RÉFÉRENCES ISOLÉES (isolated_reference) : entrées biblio hors section\n"
        "  • Des TITRES consécutifs (heading) : sous-sections non formatées\n"
        "  • De simples PARAGRAPHES COURTS (paragraph) : sans structure spéciale\n\n"
        "Réponds UNIQUEMENT avec ce JSON strict :\n"
        '{"classification":"heading|poetry_quote|list_item|isolated_reference|paragraph|uncertain",'
        '"confidence":0.0,"reason":"explication courte (1 phrase)",'
        '"recommended_action":"transform|diagnostic|ignore"}'
    )
