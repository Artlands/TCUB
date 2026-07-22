"""Harness-local result/config types. Everything else reuses taskbound-core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from taskbound_core import Action, Consequence, SecurityVerdict, ViolationRecord

__all__ = ["Defense", "Observation", "ScenarioResult"]


class Defense(Enum):
    """The defense in force for a run. M2 exercises the two anchor points; the
    intermediate controls (A1 provenance, A2 allowlist, A3 egress gate) slot in
    the same gate later."""

    A0 = "A0"  # no defense (baseline)
    A4 = "A4"  # task-scope enforcement (taskbound_core.evaluate at runtime)


@dataclass(frozen=True)
class Observation:
    """What the cluster returns after (attempting) an action."""

    ok: bool
    content: str = ""
    error: Optional[str] = None


@dataclass(frozen=True)
class ScenarioResult:
    """Outcome of running one scenario under one defense."""

    scenario_id: str
    defense: Defense
    consequence: Consequence
    security: SecurityVerdict
    utility_preserved: bool
    executed: tuple[Action, ...] = ()
    denied: tuple[tuple[Action, str], ...] = ()  # (action, reason)
    violations: tuple[ViolationRecord, ...] = ()

    @property
    def violated(self) -> bool:
        return self.security is SecurityVerdict.VIOLATED
