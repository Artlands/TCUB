"""Bench scenario schema (M4: composable with the attack registry).

A bench scenario is the AgentDojo-surface instantiation of one consequence: a
benign user task (prompt + base env + benign tool script + utility check + the
shared ``TaskPolicy``) plus an injection (a raw malicious instruction and the
site that carries it, and the malicious tool call a susceptible agent makes).

The injection *text* is produced by a swappable ``Attack`` at run time, so the
same scenario is swept across attack techniques. The policy + consequence are
identical in shape to the harness scenario, so both surfaces score one boundary.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable

from agentdojo.functions_runtime import FunctionCall

from taskbound_core import Consequence, TaskPolicy

from .env import HPCEnv
from .pipeline import DEFAULT_SYSTEM_PROMPT

__all__ = ["BenchScenario", "call"]

_UID = itertools.count()


def call(function: str, **args) -> FunctionCall:
    """Build a FunctionCall with a process-unique id (ids must be unique within a
    run so tool results pair back to their call)."""
    return FunctionCall(function=function, args=args, id=f"{function}-{next(_UID)}")


@dataclass(frozen=True)
class BenchScenario:
    id: str
    consequence: Consequence
    policy: TaskPolicy
    user_prompt: str
    base_env_factory: Callable[[], HPCEnv]  # benign world + target asset, no injection
    utility: Callable[[HPCEnv], bool]
    benign_script: tuple[FunctionCall, ...]  # what a correct agent does
    malicious_call: FunctionCall  # what a susceptible agent additionally does
    injection_site: str  # path of the file the payload is planted in
    injection_instruction: str  # raw malicious instruction (an Attack renders it)
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def susceptible_script(self) -> tuple[FunctionCall, ...]:
        return (*self.benign_script, self.malicious_call)

    def robust_script(self) -> tuple[FunctionCall, ...]:
        return self.benign_script
