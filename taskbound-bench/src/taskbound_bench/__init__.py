"""taskbound-bench -- the AgentDojo consumer of taskbound-core.

Hosts the in-memory scored matrix, the defense matrix (A0-A4 + combos), the
consequence/severity metric layer, and the two evaluation axes (reference-model
sweep + agent-product adapter). Depends on AgentDojo (pinned) and taskbound-core.
"""

from __future__ import annotations

from . import attacks, drivers, metrics, scenarios
from .attacks import Attack
from .benchmark import (
    CaseResult,
    MatrixReport,
    materialize_env,
    run_benign,
    run_case,
    run_full_matrix,
    run_matrix,
)
from .defenses import Control, Defense, ProvenanceLabeler, build_loop_elements
from .drivers import (
    AgentAdapter,
    FakeAgentAdapter,
    apply_action,
    reference_axis_sweep,
    run_case_adapter,
)
from .env import HPCEnv
from .executor import (
    ActionMapper,
    EgressGateExecutor,
    EnvAdapter,
    GatingExecutor,
    TaskScopeExecutor,
    ToolAllowlistExecutor,
)
from .mapping import hpc_action_mapper, hpc_env_adapter
from .metrics import (
    DefenseMetrics,
    benign_usr_baseline,
    compute_metrics,
    default_severity_weights,
    format_joint_table,
    severity_weighted_risk,
)
from .pipeline import DEFAULT_SYSTEM_PROMPT, ScriptedLLM, build_pipeline
from .scenario import BenchScenario
from .tools import HPC_TOOLS, register_hpc_tools

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # gating executors / defenses
    "GatingExecutor",
    "TaskScopeExecutor",
    "ToolAllowlistExecutor",
    "EgressGateExecutor",
    "ProvenanceLabeler",
    "ActionMapper",
    "EnvAdapter",
    "Control",
    "Defense",
    "build_loop_elements",
    # HPC suite
    "HPCEnv",
    "HPC_TOOLS",
    "register_hpc_tools",
    "hpc_action_mapper",
    "hpc_env_adapter",
    "BenchScenario",
    "scenarios",
    # attacks
    "attacks",
    "Attack",
    # pipeline
    "ScriptedLLM",
    "build_pipeline",
    "DEFAULT_SYSTEM_PROMPT",
    # benchmark
    "CaseResult",
    "MatrixReport",
    "materialize_env",
    "run_case",
    "run_benign",
    "run_matrix",
    "run_full_matrix",
    # metrics
    "metrics",
    "DefenseMetrics",
    "compute_metrics",
    "benign_usr_baseline",
    "default_severity_weights",
    "severity_weighted_risk",
    "format_joint_table",
    # drivers / axes
    "drivers",
    "reference_axis_sweep",
    "AgentAdapter",
    "FakeAgentAdapter",
    "run_case_adapter",
    "apply_action",
]
