from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from purh_editorial.model import Diagnostic, Transformation


class RuleFamily(str, Enum):
    ORTHOTYPOGRAPHY = "orthotypography"
    FOOTNOTE = "footnote"
    BIBLIOGRAPHY = "bibliography"
    STRUCTURE = "structure"


class RuleNature(str, Enum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"


class RuleActionType(str, Enum):
    TEXT_TRANSFORM = "text_transform"
    STYLE_TRANSFORM = "style_transform"
    STRUCTURE_TRANSFORM = "structure_transform"
    DIAGNOSTIC = "diagnostic"
    PIPELINE_CONTROL = "pipeline_control"


class DeploymentStatus(str, Enum):
    ACTIVE = "active"
    REVIEW_ONLY = "review_only"
    DISABLED = "disabled"


class DecisionOutcome(str, Enum):
    APPLY = "apply"
    REVIEW = "review"
    IGNORE = "ignore"


class EvidencePolarity(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ImplementationState(str, Enum):
    LEGACY = "legacy"
    PLANNED = "planned"
    DORMANT = "dormant"
    NATIVE = "native"


class NormativeStatus(str, Enum):
    PURH_VALIDATED = "purh_validated"
    DOCUMENTED_GENERAL = "documented_general"
    CORPUS_OBSERVED = "corpus_observed"
    INTERNAL_UNSOURCED = "internal_unsourced"
    NOT_APPLICABLE = "not_applicable"


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")


def _freeze_json_value(value: Any, field_name: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool, Enum)):
        return value
    if isinstance(value, tuple):
        return tuple(_freeze_json_value(item, field_name) for item in value)
    if isinstance(value, list):
        return tuple(_freeze_json_value(item, field_name) for item in value)
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{field_name} mapping keys must be strings")
            frozen[key] = _freeze_json_value(item, field_name)
        return MappingProxyType(frozen)
    raise TypeError(
        f"{field_name} contains a non-JSON-compatible value: "
        f"{type(value).__name__}"
    )


def _freeze_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping or None")
    frozen = _freeze_json_value(value, field_name)
    assert isinstance(frozen, Mapping)
    return frozen


def to_json_data(value: Any) -> Any:
    """Convertit les types du socle en structures JSON natives.

    La fonction est volontairement stricte : elle n'accepte ni callback, ni
    proxy COM, ni regex, ni objet applicatif arbitraire.
    """

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_data(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON mapping keys must be strings")
            result[key] = to_json_data(item)
        return result
    if isinstance(value, (tuple, list)):
        return [to_json_data(item) for item in value]
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class NormativeSource:
    source_id: str
    authority: str
    title: str
    status: NormativeStatus
    version: str | None = None
    locator: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.source_id, "source_id")
        _require_non_empty(self.authority, "authority")
        _require_non_empty(self.title, "title")
        if not isinstance(self.status, NormativeStatus):
            raise TypeError("status must be a NormativeStatus")


@dataclass(frozen=True, slots=True)
class RuleDescriptor:
    rule_id: str
    owner_module: str
    family: RuleFamily
    nature: RuleNature
    action_type: RuleActionType
    deployment_status: DeploymentStatus
    normative_status: NormativeStatus
    normative_sources: tuple[NormativeSource, ...]
    protection_policy_id: str
    score_family: str | None = None
    legacy_aliases: tuple[str, ...] = ()
    test_refs: tuple[str, ...] = ()
    implementation_state: ImplementationState = ImplementationState.LEGACY

    def __post_init__(self) -> None:
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.owner_module, "owner_module")
        _require_non_empty(self.protection_policy_id, "protection_policy_id")
        _require_tuple(self.normative_sources, "normative_sources")
        _require_tuple(self.legacy_aliases, "legacy_aliases")
        _require_tuple(self.test_refs, "test_refs")
        if not isinstance(self.family, RuleFamily):
            raise TypeError("family must be a RuleFamily")
        if not isinstance(self.nature, RuleNature):
            raise TypeError("nature must be a RuleNature")
        if not isinstance(self.action_type, RuleActionType):
            raise TypeError("action_type must be a RuleActionType")
        if not isinstance(self.deployment_status, DeploymentStatus):
            raise TypeError("deployment_status must be a DeploymentStatus")
        if not isinstance(self.normative_status, NormativeStatus):
            raise TypeError("normative_status must be a NormativeStatus")
        if not isinstance(self.implementation_state, ImplementationState):
            raise TypeError("implementation_state must be an ImplementationState")
        if self.nature is RuleNature.DETERMINISTIC and self.score_family is not None:
            raise ValueError("deterministic rules cannot define score_family")
        if (
            self.nature is RuleNature.HEURISTIC
            and self.implementation_state is ImplementationState.NATIVE
            and not (self.score_family and self.score_family.strip())
        ):
            raise ValueError("native heuristic rules must define score_family")
        if self.score_family is not None:
            _require_non_empty(self.score_family, "score_family")
        if self.rule_id in self.legacy_aliases:
            raise ValueError("legacy_aliases cannot contain rule_id")
        if any(not isinstance(source, NormativeSource) for source in self.normative_sources):
            raise TypeError("normative_sources must contain NormativeSource values")
        if any(not isinstance(alias, str) or not alias.strip() for alias in self.legacy_aliases):
            raise ValueError("legacy_aliases must contain non-empty strings")
        if any(not isinstance(ref, str) or not ref.startswith("tests/") for ref in self.test_refs):
            raise ValueError("test_refs must be non-empty paths under tests/")
        source_statuses = {source.status for source in self.normative_sources}
        required_source_status = {
            NormativeStatus.PURH_VALIDATED: NormativeStatus.PURH_VALIDATED,
            NormativeStatus.DOCUMENTED_GENERAL: NormativeStatus.DOCUMENTED_GENERAL,
            NormativeStatus.CORPUS_OBSERVED: NormativeStatus.CORPUS_OBSERVED,
        }.get(self.normative_status)
        if (
            required_source_status is not None
            and required_source_status not in source_statuses
        ):
            raise ValueError(
                f"{self.normative_status.value} rules require a matching source status"
            )
        if self.normative_status is NormativeStatus.INTERNAL_UNSOURCED and (
            source_statuses
            & {
                NormativeStatus.PURH_VALIDATED,
                NormativeStatus.DOCUMENTED_GENERAL,
                NormativeStatus.CORPUS_OBSERVED,
            }
        ):
            raise ValueError(
                "internal_unsourced rules cannot claim a documented normative source"
            )


@dataclass(frozen=True, slots=True)
class ProtectionDecision:
    protected: bool
    policy_id: str
    reasons: tuple[str, ...]
    inherited_from: tuple[str, ...] = ()
    legacy_behavior: bool = False

    def __post_init__(self) -> None:
        _require_non_empty(self.policy_id, "policy_id")
        _require_tuple(self.reasons, "reasons")
        _require_tuple(self.inherited_from, "inherited_from")
        if self.protected and not self.reasons:
            raise ValueError("a protected decision must provide at least one reason")


@dataclass(frozen=True, slots=True)
class CompatibilityContext:
    source_config_version: str | None
    legacy_profile: str | None = None
    legacy_decision_mode: str | None = None
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_tuple(self.flags, "flags")


@dataclass(frozen=True, slots=True)
class RuleContext:
    document_id: str
    target_refs: tuple[str, ...]
    source_facts: Mapping[str, Any]
    canonical_facts: Mapping[str, Any]
    protection: ProtectionDecision
    compatibility: CompatibilityContext

    def __post_init__(self) -> None:
        _require_non_empty(self.document_id, "document_id")
        _require_tuple(self.target_refs, "target_refs")
        object.__setattr__(
            self,
            "source_facts",
            _freeze_mapping(self.source_facts, "source_facts"),
        )
        object.__setattr__(
            self,
            "canonical_facts",
            _freeze_mapping(self.canonical_facts, "canonical_facts"),
        )


@dataclass(frozen=True, slots=True)
class ProposedAction:
    action_type: RuleActionType
    target_refs: tuple[str, ...]
    before: Any | None = None
    after: Any | None = None
    offset_start: int | None = None
    offset_end: int | None = None
    style_patch: Mapping[str, Any] | None = None
    semantic_patch: Mapping[str, Any] | None = None
    control_payload: Mapping[str, Any] | None = None
    created_refs: tuple[str, ...] = ()
    deleted_refs: tuple[str, ...] = ()
    merged_refs: tuple[str, ...] = ()
    diagnostic_payload: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, RuleActionType):
            raise TypeError("action_type must be a RuleActionType")
        _require_tuple(self.target_refs, "target_refs")
        _require_tuple(self.created_refs, "created_refs")
        _require_tuple(self.deleted_refs, "deleted_refs")
        _require_tuple(self.merged_refs, "merged_refs")
        if not self.target_refs or any(not ref for ref in self.target_refs):
            raise ValueError("ProposedAction requires at least one target")
        if (self.offset_start is None) != (self.offset_end is None):
            raise ValueError("offset_start and offset_end must be provided together")
        if self.offset_start is not None:
            if self.offset_start < 0 or self.offset_end is None or self.offset_end < 0:
                raise ValueError("offsets must be non-negative")
            if self.offset_end < self.offset_start:
                raise ValueError("offset_end must be greater than or equal to offset_start")

        object.__setattr__(self, "before", _freeze_json_value(self.before, "before"))
        object.__setattr__(self, "after", _freeze_json_value(self.after, "after"))
        for name in (
            "style_patch",
            "semantic_patch",
            "control_payload",
            "diagnostic_payload",
        ):
            object.__setattr__(
                self,
                name,
                _freeze_mapping(getattr(self, name), name),
            )

        structure_refs = self.created_refs or self.deleted_refs or self.merged_refs
        if self.action_type is RuleActionType.DIAGNOSTIC:
            if self.diagnostic_payload is None:
                raise ValueError("diagnostic actions require diagnostic_payload")
            if self.style_patch or self.semantic_patch or self.control_payload or structure_refs:
                raise ValueError("diagnostic action contains incompatible fields")
        elif self.action_type is RuleActionType.STYLE_TRANSFORM:
            if self.style_patch is None:
                raise ValueError("style transformations require style_patch")
            if self.diagnostic_payload or self.semantic_patch or self.control_payload or structure_refs:
                raise ValueError("style transformation contains incompatible fields")
        elif self.action_type is RuleActionType.STRUCTURE_TRANSFORM:
            if self.style_patch or self.diagnostic_payload or self.control_payload:
                raise ValueError("structure transformation contains incompatible fields")
        elif self.action_type is RuleActionType.TEXT_TRANSFORM:
            if (
                self.style_patch
                or self.semantic_patch
                or self.control_payload
                or self.diagnostic_payload
                or structure_refs
            ):
                raise ValueError("text transformation contains incompatible fields")
        elif self.action_type is RuleActionType.PIPELINE_CONTROL:
            if self.control_payload is None:
                raise ValueError("pipeline controls require control_payload")
            if self.style_patch or self.semantic_patch or self.diagnostic_payload or structure_refs:
                raise ValueError("pipeline control contains incompatible fields")


_MUTATING_ACTIONS = {
    RuleActionType.TEXT_TRANSFORM,
    RuleActionType.STYLE_TRANSFORM,
    RuleActionType.STRUCTURE_TRANSFORM,
}


@dataclass(frozen=True, slots=True)
class DeterministicResult:
    rule_id: str
    matched: bool
    target_refs: tuple[str, ...]
    proposed_actions: tuple[ProposedAction, ...]
    conditions_met: tuple[str, ...]
    veto_reasons: tuple[str, ...]
    justification: str

    def __post_init__(self) -> None:
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.justification, "justification")
        _require_tuple(self.target_refs, "target_refs")
        _require_tuple(self.proposed_actions, "proposed_actions")
        _require_tuple(self.conditions_met, "conditions_met")
        _require_tuple(self.veto_reasons, "veto_reasons")
        if any(not isinstance(action, ProposedAction) for action in self.proposed_actions):
            raise TypeError("proposed_actions must contain ProposedAction values")
        if not self.matched and self.proposed_actions:
            raise ValueError("a non-match cannot propose an action")
        if self.veto_reasons and any(
            action.action_type in _MUTATING_ACTIONS
            for action in self.proposed_actions
        ):
            raise ValueError("a veto forbids mutating actions")
        if self.matched and not self.proposed_actions and not self.justification.strip():
            raise ValueError("actionless matches require an abstention justification")


@dataclass(frozen=True, slots=True)
class HeuristicEvidence:
    code: str
    polarity: EvidencePolarity
    value: Any
    contribution: float | None
    explanation: str

    def __post_init__(self) -> None:
        _require_non_empty(self.code, "code")
        _require_non_empty(self.explanation, "explanation")
        if not isinstance(self.polarity, EvidencePolarity):
            raise TypeError("polarity must be an EvidencePolarity")
        object.__setattr__(self, "value", _freeze_json_value(self.value, "value"))


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

    def __post_init__(self) -> None:
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.score_family, "score_family")
        _require_non_empty(self.justification, "justification")
        _require_tuple(self.proposed_actions, "proposed_actions")
        _require_tuple(self.target_refs, "target_refs")
        _require_tuple(self.positive_evidence, "positive_evidence")
        _require_tuple(self.negative_evidence, "negative_evidence")
        _require_tuple(self.veto_reasons, "veto_reasons")
        if any(not isinstance(action, ProposedAction) for action in self.proposed_actions):
            raise TypeError("proposed_actions must contain ProposedAction values")
        if any(
            not isinstance(item, HeuristicEvidence)
            for item in self.positive_evidence + self.negative_evidence
        ):
            raise TypeError("evidence collections must contain HeuristicEvidence values")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
        if not self.target_refs:
            raise ValueError("HeuristicProposal requires at least one target")
        positive_codes = {item.code for item in self.positive_evidence}
        negative_codes = {item.code for item in self.negative_evidence}
        veto_codes = set(self.veto_reasons)
        if any(
            item.polarity is not EvidencePolarity.POSITIVE
            for item in self.positive_evidence
        ):
            raise ValueError("positive_evidence must contain positive evidence")
        if any(
            item.polarity is not EvidencePolarity.NEGATIVE
            for item in self.negative_evidence
        ):
            raise ValueError("negative_evidence must contain negative evidence")
        if positive_codes & negative_codes:
            raise ValueError("positive and negative evidence codes must be distinct")
        if (positive_codes | negative_codes) & veto_codes:
            raise ValueError("evidence codes must be distinct from veto reasons")
        if not self.proposed_actions and not self.veto_reasons:
            raise ValueError("a heuristic proposal requires an action or a veto")


@dataclass(frozen=True, slots=True)
class ThresholdPair:
    review: float
    apply: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.review <= self.apply <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= review <= apply <= 1")


@dataclass(frozen=True, slots=True)
class RuleDecision:
    decision_id: str
    sequence: int
    rule_id: str
    nature: RuleNature
    implementation_state: ImplementationState
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

    def __post_init__(self) -> None:
        _require_non_empty(self.decision_id, "decision_id")
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.reason_code, "reason_code")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        _require_tuple(self.target_refs, "target_refs")
        _require_tuple(self.proposed_actions, "proposed_actions")
        _require_tuple(self.evidence, "evidence")
        _require_tuple(self.veto_reasons, "veto_reasons")
        _require_tuple(self.compatibility_flags, "compatibility_flags")
        if not isinstance(self.nature, RuleNature):
            raise TypeError("nature must be a RuleNature")
        if not isinstance(self.implementation_state, ImplementationState):
            raise TypeError("implementation_state must be an ImplementationState")
        if not isinstance(self.deployment_status, DeploymentStatus):
            raise TypeError("deployment_status must be a DeploymentStatus")
        if not isinstance(self.outcome, DecisionOutcome):
            raise TypeError("outcome must be a DecisionOutcome")
        if any(not isinstance(action, ProposedAction) for action in self.proposed_actions):
            raise TypeError("proposed_actions must contain ProposedAction values")
        if any(not isinstance(item, HeuristicEvidence) for item in self.evidence):
            raise TypeError("evidence must contain HeuristicEvidence values")
        if not self.target_refs:
            raise ValueError("RuleDecision requires at least one target")
        if self.nature is RuleNature.DETERMINISTIC:
            if any(
                value is not None
                for value in (
                    self.score_family,
                    self.score,
                    self.review_threshold,
                    self.apply_threshold,
                )
            ):
                raise ValueError("deterministic decisions cannot define scores or thresholds")
        elif self.nature is RuleNature.HEURISTIC:
            if (
                self.implementation_state is ImplementationState.NATIVE
                and (self.score is None or not self.score_family)
            ):
                raise ValueError("native heuristic decisions require score and score_family")
            if self.score is not None and not 0.0 <= self.score <= 1.0:
                raise ValueError("score must be between 0 and 1")
            if (self.review_threshold is None) != (self.apply_threshold is None):
                raise ValueError("review and apply thresholds must be provided together")
            if self.review_threshold is not None:
                ThresholdPair(self.review_threshold, self.apply_threshold)  # type: ignore[arg-type]
        if (
            self.deployment_status is DeploymentStatus.DISABLED
            and self.outcome is not DecisionOutcome.IGNORE
        ):
            raise ValueError("disabled rules can only produce ignore decisions")
        if (
            self.deployment_status is DeploymentStatus.REVIEW_ONLY
            and self.outcome is DecisionOutcome.APPLY
        ):
            raise ValueError("review_only rules cannot produce apply decisions")
        if self.outcome in {DecisionOutcome.APPLY, DecisionOutcome.REVIEW} and not self.proposed_actions:
            raise ValueError("apply and review decisions require proposed actions")
        if self.outcome is DecisionOutcome.APPLY and self.veto_reasons:
            raise ValueError("a veto forbids an apply decision")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    decision_id: str
    applied: bool
    transformations: tuple[Transformation, ...]
    diagnostics: tuple[Diagnostic, ...]
    before_signature: str
    after_signature: str

    def __post_init__(self) -> None:
        _require_non_empty(self.decision_id, "decision_id")
        _require_tuple(self.transformations, "transformations")
        _require_tuple(self.diagnostics, "diagnostics")
        _require_non_empty(self.before_signature, "before_signature")
        _require_non_empty(self.after_signature, "after_signature")
