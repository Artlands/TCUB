"""Shared value types for taskbound-core.

Everything here is a plain, frozen dataclass or enum -- no I/O, no third-party
deps -- so the whole trust anchor is trivially auditable and installs anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional

__all__ = [
    "ActionType",
    "Action",
    "Consequence",
    "Effect",
    "SecurityVerdict",
    "ViolationRecord",
    "Decision",
    "OracleResult",
]


class ActionType(Enum):
    """The kinds of agent action the policy engine reasons about."""

    READ = "read"          # read a file / dataset path
    WRITE = "write"        # create or append to a path
    EDIT = "edit"          # modify an existing artifact in place
    SUBMIT_JOB = "submit_job"  # submit / resize a scheduler job
    EGRESS = "egress"      # send data to an external sink (e.g. the LLM backend)


class Consequence(Enum):
    """The four HPC-distinctive consequence types TaskBound scores.

    Mirrors development-plan §4. ``CROSS_PROJECT_READ`` is the bridge case
    (closest to generic prompt injection); the other three are HPC-native.
    """

    CROSS_PROJECT_READ = "cross_project_read"
    RESOURCE_ABUSE = "resource_abuse"
    INTEGRITY_TAMPERING = "integrity_tampering"
    SHARED_FS_PERSISTENCE = "shared_fs_persistence"


class Effect(Enum):
    """A single policy decision on a single action."""

    ALLOW = "allow"
    DENY = "deny"


class SecurityVerdict(Enum):
    """A whole-trace oracle verdict for one targeted consequence."""

    SECURE = "SECURE"
    VIOLATED = "VIOLATED"


@dataclass(frozen=True)
class Action:
    """A normalized agent action.

    Both evaluation surfaces (the AgentDojo bench and the real-cluster harness)
    normalize their agent's behavior into a trace of these, so the same engine
    and oracle score both surfaces identically.
    """

    type: ActionType
    path: Optional[str] = None
    project: Optional[str] = None
    sink: Optional[str] = None
    payload: str = ""
    nodes: int = 0
    gpus: int = 0
    walltime_minutes: int = 0
    jobs: int = 1
    label: str = ""  # optional human-readable tag for traces / debugging


@dataclass(frozen=True)
class ViolationRecord:
    """Emitted when the engine denies an action.

    ``consequence`` is the best-effort classification into one of the four
    scored types; it is ``None`` for a plain out-of-scope action that the A4
    control blocks but that maps to no named HPC consequence.
    """

    consequence: Optional[Consequence]
    action: Action
    reason: str
    detail: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    """The result of evaluating one action against one policy."""

    effect: Effect
    reason: str = ""
    violation: Optional[ViolationRecord] = None

    @property
    def allowed(self) -> bool:
        return self.effect is Effect.ALLOW

    @property
    def denied(self) -> bool:
        return self.effect is Effect.DENY


@dataclass(frozen=True)
class OracleResult:
    """A whole-trace security verdict for one targeted consequence."""

    verdict: SecurityVerdict
    consequence: Consequence
    violations: tuple[ViolationRecord, ...] = ()

    @property
    def violated(self) -> bool:
        return self.verdict is SecurityVerdict.VIOLATED

    @property
    def secure(self) -> bool:
        return self.verdict is SecurityVerdict.SECURE
