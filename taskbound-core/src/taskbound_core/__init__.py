"""taskbound-core -- the dependency-free trust anchor for TaskBound.

Defines the task boundary ("user-broad, task-narrow") and what counts as a
violation, once, so the AgentDojo bench and the real-cluster harness are
equivalent by construction. Imports nothing outside the standard library.
"""

from __future__ import annotations

from .engine import PolicyEngine, evaluate
from .env import EnvironmentState
from .glob import path_matches
from .oracle import all_violations, security_oracle
from .policy import EgressPolicy, PathScope, ResourceCeiling, TaskPolicy
from .types import (
    Action,
    ActionType,
    Consequence,
    Decision,
    Effect,
    OracleResult,
    SecurityVerdict,
    ViolationRecord,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # policy
    "TaskPolicy",
    "PathScope",
    "ResourceCeiling",
    "EgressPolicy",
    # env
    "EnvironmentState",
    # engine
    "PolicyEngine",
    "evaluate",
    # oracle
    "security_oracle",
    "all_violations",
    # types
    "Action",
    "ActionType",
    "Consequence",
    "Decision",
    "Effect",
    "SecurityVerdict",
    "ViolationRecord",
    # utils
    "path_matches",
]
