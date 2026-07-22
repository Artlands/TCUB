"""Bench scenario registry. M3 ships the first (cross_project_read); the other
three consequences are added at M4."""

from __future__ import annotations

from ..scenario import BenchScenario
from .cross_project_read import SCENARIO as cross_project_read

__all__ = ["REGISTRY", "all_scenarios", "get"]

_SCENARIOS = [cross_project_read]

REGISTRY: dict[str, BenchScenario] = {s.id: s for s in _SCENARIOS}


def all_scenarios() -> list[BenchScenario]:
    return list(_SCENARIOS)


def get(scenario_id: str) -> BenchScenario:
    return REGISTRY[scenario_id]
