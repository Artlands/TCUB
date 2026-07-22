"""Declarative scenario schema (development-plan §4.1) + seed->EnvironmentState.

A scenario is a self-contained record: the benign task, the task policy (ground
truth for both scoring and defense), the injection, the targeted consequence,
and the equivalence contract (`expected`). One `ClusterSeed` seeds *both* the
runnable cluster and the `EnvironmentState` the oracle judges against, so they
cannot disagree.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping

from taskbound_core import (
    Action,
    Consequence,
    EnvironmentState,
    SecurityVerdict,
    TaskPolicy,
    path_matches,
)

__all__ = ["ClusterSeed", "Injection", "Expected", "Scenario", "env_from_seed"]


@dataclass(frozen=True)
class ClusterSeed:
    """Initial world state: files, which project owns what, which paths are
    shared/durable, planted canaries, and which globs are declared-immutable."""

    files: Mapping[str, str] = field(default_factory=dict)
    file_projects: Mapping[str, str] = field(default_factory=dict)  # glob -> project
    shared_globs: tuple[str, ...] = ()
    canaries: Mapping[str, str] = field(default_factory=dict)  # token -> guarded location
    immutable_globs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Injection:
    """The attacker payload and where it lives (mapped to paper capabilities)."""

    site: str  # which piece of environment text carries it
    payload: str
    capability: str  # C1..C5 tag from the position paper


@dataclass(frozen=True)
class Expected:
    """The equivalence contract the real cluster is validated against."""

    a0: SecurityVerdict = SecurityVerdict.VIOLATED
    a4: SecurityVerdict = SecurityVerdict.SECURE
    utility_a4: bool = True


@dataclass(frozen=True)
class Scenario:
    id: str
    consequence: Consequence
    description: str
    policy: TaskPolicy
    seed: ClusterSeed
    benign_actions: tuple[Action, ...]
    malicious_action: Action
    injection: Injection
    expected: Expected = field(default_factory=Expected)


def env_from_seed(seed: ClusterSeed) -> EnvironmentState:
    """Derive the pure `EnvironmentState` the oracle/gate reason over.

    Immutable-artifact hashes are recorded up front so downstream tooling can
    corroborate an `integrity_tampering` verdict by snapshot/diff.
    """
    immutable_hashes = {
        path: hashlib.sha256(content.encode()).hexdigest()
        for path, content in seed.files.items()
        if any(path_matches(path, g) for g in seed.immutable_globs)
    }
    return EnvironmentState(
        path_project=dict(seed.file_projects),
        shared_globs=tuple(seed.shared_globs),
        canaries=dict(seed.canaries),
        immutable_hashes=immutable_hashes,
    )
