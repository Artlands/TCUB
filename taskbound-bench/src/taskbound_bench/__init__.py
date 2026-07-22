"""taskbound-bench -- the AgentDojo consumer of taskbound-core.

Hosts the in-memory scored matrix and the ``TaskScopeExecutor`` (A4 defense),
which enforces the shared ``taskbound_core.PolicyEngine`` inside AgentDojo's
agent pipeline. Depends on AgentDojo (pinned) and taskbound-core.
"""

from __future__ import annotations

from . import scenarios
from .benchmark import CaseResult, Defense, run_case, run_matrix
from .env import HPCEnv
from .executor import ActionMapper, EnvAdapter, TaskScopeExecutor
from .mapping import hpc_action_mapper, hpc_env_adapter
from .pipeline import DEFAULT_SYSTEM_PROMPT, ScriptedLLM, build_pipeline
from .scenario import BenchScenario
from .tools import HPC_TOOLS, register_hpc_tools

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # A4 defense (M1)
    "TaskScopeExecutor",
    "ActionMapper",
    "EnvAdapter",
    # HPC suite (M3)
    "HPCEnv",
    "HPC_TOOLS",
    "register_hpc_tools",
    "hpc_action_mapper",
    "hpc_env_adapter",
    "BenchScenario",
    "scenarios",
    # pipeline
    "ScriptedLLM",
    "build_pipeline",
    "DEFAULT_SYSTEM_PROMPT",
    # benchmark
    "Defense",
    "CaseResult",
    "run_case",
    "run_matrix",
]
