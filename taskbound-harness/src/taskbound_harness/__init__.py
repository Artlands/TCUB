"""taskbound-harness -- the stdlib-only, real-cluster consumer of taskbound-core.

The permanent real-Slurm validation path. Installs on a locked-down login node
(only dependency is taskbound-core, itself stdlib-only). Drives an agent through
a cluster adapter, enforces the shared taskbound_core policy engine as the A4
defense, and scores with the shared oracle -- so its verdicts are equivalent by
construction to the AgentDojo bench's.
"""

from __future__ import annotations

from . import scenarios
from .cluster import ClusterAdapter, SlurmClusterAdapter, StubCluster
from .driver import (
    Driver,
    OpenAIChatDriver,
    ScriptedDriver,
    robust_trace,
    susceptible_trace,
)
from .runner import run_scenario, verify_scenario
from .scenario import ClusterSeed, Expected, Injection, Scenario, env_from_seed
from .types import Defense, Observation, ScenarioResult

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # scenarios
    "scenarios",
    "Scenario",
    "ClusterSeed",
    "Injection",
    "Expected",
    "env_from_seed",
    # run
    "run_scenario",
    "verify_scenario",
    "Defense",
    "Observation",
    "ScenarioResult",
    # drivers
    "Driver",
    "ScriptedDriver",
    "OpenAIChatDriver",
    "susceptible_trace",
    "robust_trace",
    # clusters
    "ClusterAdapter",
    "StubCluster",
    "SlurmClusterAdapter",
]
