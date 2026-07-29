from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from purh_editorial.rules.model import (
    DeterministicResult,
    ExecutionResult,
    HeuristicProposal,
    ProposedAction,
    RuleContext,
    RuleDecision,
    RuleDescriptor,
    RuleFamily,
    RuleNature,
    RuleActionType,
    DeploymentStatus,
    ThresholdPair,
)

if TYPE_CHECKING:
    from purh_editorial.model import Document


class DeterministicRule(Protocol):
    descriptor: RuleDescriptor

    def evaluate(self, context: RuleContext) -> DeterministicResult:
        ...


class HeuristicRule(Protocol):
    descriptor: RuleDescriptor

    def evaluate(self, context: RuleContext) -> HeuristicProposal:
        ...


class RuleRegistry(Protocol):
    def get(self, rule_id: str) -> RuleDescriptor:
        ...

    def all(self) -> tuple[RuleDescriptor, ...]:
        ...

    def by_family(self, family: RuleFamily) -> tuple[RuleDescriptor, ...]:
        ...

    def by_nature(self, nature: RuleNature) -> tuple[RuleDescriptor, ...]:
        ...

    def by_action(self, action: RuleActionType) -> tuple[RuleDescriptor, ...]:
        ...

    def by_status(self, status: DeploymentStatus) -> tuple[RuleDescriptor, ...]:
        ...

    def validate(self) -> tuple[str, ...]:
        ...


class ProtectionResolver(Protocol):
    def resolve(
        self,
        *,
        descriptor: RuleDescriptor,
        document: Document,
        target_refs: tuple[str, ...],
    ) -> "ProtectionDecision":
        ...


class ThresholdPolicy(Protocol):
    def thresholds(
        self,
        *,
        score_family: str,
        intervention_level: int,
    ) -> ThresholdPair:
        ...


class ActionExecutor(Protocol):
    def execute(
        self,
        *,
        decision: RuleDecision,
        document: Document,
    ) -> ExecutionResult:
        ...


if TYPE_CHECKING:
    from purh_editorial.rules.model import ProtectionDecision

