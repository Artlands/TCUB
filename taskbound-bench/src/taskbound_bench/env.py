"""In-memory HPC ``TaskEnvironment`` for the AgentDojo bench.

A pydantic env (AgentDojo's ``TaskEnvironment``) modeling the minimum HPC world
the four consequence types need: a project-scoped filesystem, a scheduler, shared
scratch, declared-immutable artifacts, and planted canaries. Tools mutate it;
``mapping.hpc_env_adapter`` derives the pure ``taskbound_core.EnvironmentState``
the policy engine and oracle reason over.
"""

from __future__ import annotations

from agentdojo.functions_runtime import TaskEnvironment
from pydantic import Field

__all__ = ["HPCEnv"]


class HPCEnv(TaskEnvironment):
    files: dict[str, str] = Field(default_factory=dict)  # path -> content
    file_projects: dict[str, str] = Field(default_factory=dict)  # glob -> project
    shared_globs: list[str] = Field(default_factory=list)
    immutable_globs: list[str] = Field(default_factory=list)
    canaries: dict[str, str] = Field(default_factory=dict)  # token -> guarded location

    # effects recorded as the agent acts
    jobs: list[dict] = Field(default_factory=list)
    writes: list[str] = Field(default_factory=list)
    egress_log: list[dict] = Field(default_factory=list)
