"""Bench scenario registry: all four HPC-distinctive consequence types, each with
multiple user/injection tasks."""

from __future__ import annotations

from ..scenario import BenchScenario
from .cross_project_read import SCENARIOS as _cpr
from .integrity_tampering import SCENARIOS as _it
from .resource_abuse import SCENARIOS as _ra
from .shared_fs_persistence import SCENARIOS as _sfp

__all__ = ["REGISTRY", "all_scenarios", "get", "by_consequence"]

_SCENARIOS = [*_cpr, *_ra, *_it, *_sfp]

REGISTRY: dict[str, BenchScenario] = {s.id: s for s in _SCENARIOS}


def all_scenarios() -> list[BenchScenario]:
    return list(_SCENARIOS)


def get(scenario_id: str) -> BenchScenario:
    return REGISTRY[scenario_id]


def by_consequence(consequence) -> list[BenchScenario]:
    return [s for s in _SCENARIOS if s.consequence is consequence]
