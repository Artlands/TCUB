"""The scenario registry: the four HPC-distinctive consequence types."""

from __future__ import annotations

from ..scenario import Scenario
from .cross_project_read import SCENARIO as cross_project_read
from .integrity_tampering import SCENARIO as integrity_tampering
from .resource_abuse import SCENARIO as resource_abuse
from .shared_fs_persistence import SCENARIO as shared_fs_persistence

__all__ = ["REGISTRY", "all_scenarios", "get"]

_SCENARIOS = [
    cross_project_read,
    resource_abuse,
    integrity_tampering,
    shared_fs_persistence,
]

REGISTRY: dict[str, Scenario] = {s.id: s for s in _SCENARIOS}


def all_scenarios() -> list[Scenario]:
    return list(_SCENARIOS)


def get(scenario_id: str) -> Scenario:
    return REGISTRY[scenario_id]
