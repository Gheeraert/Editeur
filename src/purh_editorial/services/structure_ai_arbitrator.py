from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from purh_editorial.model import Diagnostic, Document, Evidence
from purh_editorial.utils import make_id

ALLOWED_CLASSIFICATIONS = {
    "heading",
    "poetry_quote",
    "paragraph",
    "reference",
    "caption",
    "bibliography",
    "uncertain",
}

ALLOWED_RECOMMENDED_ACTIONS = {"transform", "diagnostic", "ignore"}
ALLOWED_AI_AGGRESSIVENESS = {"conservative", "balanced", "aggressive"}

_ARBITRATION_RULE_ID = "R-STRUCT-AI-LOCAL-001"
_ARBITRATION_CATEGORY = "structure_ai_arbitration"


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
    max_tokens: int = 180


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
        # Aggressive means lower confidence for enriched diagnostics only.
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
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 20,
        temperature: float = 0.0,
        max_tokens: int = 180,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu arbitres uniquement un candidat structurel local. "
                        "Tu ne réécris jamais le texte. "
                        "Tu réponds uniquement en JSON strict."
                    ),
                },
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


def build_structure_ai_prompt(candidate: AiArbitrationCandidate) -> str:
    evidence_json = json.dumps(candidate.evidence, ensure_ascii=False)
    target_refs = ", ".join(candidate.target_refs)
    return (
        "Arbitrage local structurel (zone grise). Ne réécris pas le texte.\n"
        f"Type candidat: {candidate.candidate_type}\n"
        f"Target refs: {target_refs}\n"
        f"Score heuristique: {candidate.score}\n"
        f"Decision heuristique actuelle: {candidate.decision}\n"
        f"Extrait: {candidate.excerpt}\n"
        f"Contexte avant: {candidate.context_before}\n"
        f"Contexte après: {candidate.context_after}\n"
        f"Evidence: {evidence_json}\n\n"
        "Réponds UNIQUEMENT avec ce JSON strict:\n"
        '{"classification":"heading|poetry_quote|paragraph|reference|caption|bibliography|uncertain",'
        '"confidence":0.0,"reason":"court","recommended_action":"transform|diagnostic|ignore"}'
    )


def parse_structure_ai_json(raw: str) -> AiArbitrationResult:
    text = raw.strip()
    if not text:
        raise ValueError("empty_response")
    data = json.loads(text)
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
        if not enable_ai:
            return [], [], 0
        if self.provider is None:
            return [], ["Structure AI arbitration skipped: no provider configured."], 0

        results: list[Diagnostic] = []
        warnings: list[str] = []
        # Number of attempted provider calls (successful or not).
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
                severity = "info"
                message = "Arbitrage IA local: classification exploitable pour revue humaine."
            else:
                severity = "info"
                message = "Arbitrage IA local incertain: conserver un diagnostic prudent."

            results.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity=severity,
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

    @staticmethod
    def _candidate_from_diagnostic(
        *,
        document: Document,
        diagnostic: Diagnostic,
    ) -> AiArbitrationCandidate | None:
        if diagnostic.rule_id not in {"R-STRUCT-HEADING-001", "R-CI-POETRY-001"}:
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

        excerpt = ""
        if isinstance(evidence.get("excerpt"), str):
            excerpt = evidence["excerpt"]
        if not excerpt and diagnostic.evidence and diagnostic.evidence.excerpt:
            excerpt = diagnostic.evidence.excerpt

        context_before, context_after = _local_context(document=document, target_ref=target_refs[0] if target_refs else "")
        candidate_type = "heading" if diagnostic.rule_id == "R-STRUCT-HEADING-001" else "poetry"

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


def _local_context(*, document: Document, target_ref: str) -> tuple[str, str]:
    if not target_ref:
        return "", ""
    for index, block in enumerate(document.blocks):
        if block.block_id != target_ref:
            continue
        before = document.blocks[index - 1].text.strip() if index > 0 else ""
        after = document.blocks[index + 1].text.strip() if index + 1 < len(document.blocks) else ""
        return before[:180], after[:180]
    return "", ""
