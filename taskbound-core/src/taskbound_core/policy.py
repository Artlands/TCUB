"""``TaskPolicy`` -- the declared scope of a single task.

This is the executable form of the paper's thesis: authority the *task* has,
as distinct from authority the *account* has. It is the single ground truth for
both scoring (offline replay) and defense (``TaskScopeExecutor`` at runtime).

See development-plan §5.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from .glob import path_matches

__all__ = ["PathScope", "ResourceCeiling", "EgressPolicy", "TaskPolicy"]


@dataclass(frozen=True)
class PathScope:
    """Read/write/immutable path globs the task is scoped to.

    Empty ``readable``/``writable`` tuples mean "unconstrained on this axis"
    (a permissive default); a scenario tightens the scope by listing globs.
    ``immutable`` always constrains: any match is a declared-immutable artifact.
    """

    readable: tuple[str, ...] = ()
    writable: tuple[str, ...] = ()
    immutable: tuple[str, ...] = ()

    def is_readable(self, path: str) -> bool:
        return any(path_matches(path, g) for g in self.readable)

    def is_writable(self, path: str) -> bool:
        return any(path_matches(path, g) for g in self.writable)

    def is_immutable(self, path: str) -> bool:
        return any(path_matches(path, g) for g in self.immutable)


@dataclass(frozen=True)
class ResourceCeiling:
    """Per-task scheduler ceiling. ``None`` on a field means "no limit"."""

    max_nodes: Optional[int] = None
    max_gpus: Optional[int] = None
    max_walltime_minutes: Optional[int] = None
    max_jobs: Optional[int] = None


@dataclass(frozen=True)
class EgressPolicy:
    """Sanctioned egress sinks. A canary sink is *never* listed here."""

    allowed_sinks: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TaskPolicy:
    """Everything *this task* is permitted to touch."""

    task_id: str
    projects: frozenset[str] = frozenset()
    paths: PathScope = field(default_factory=PathScope)
    resources: ResourceCeiling = field(default_factory=ResourceCeiling)
    egress: EgressPolicy = field(default_factory=EgressPolicy)

    @staticmethod
    def build(
        task_id: str,
        *,
        projects: Iterable[str] = (),
        readable: Iterable[str] = (),
        writable: Iterable[str] = (),
        immutable: Iterable[str] = (),
        max_nodes: Optional[int] = None,
        max_gpus: Optional[int] = None,
        max_walltime_minutes: Optional[int] = None,
        max_jobs: Optional[int] = None,
        allowed_sinks: Iterable[str] = (),
    ) -> "TaskPolicy":
        """Ergonomic constructor from loose iterables (e.g. a scenario file)."""
        return TaskPolicy(
            task_id=task_id,
            projects=frozenset(projects),
            paths=PathScope(
                readable=tuple(readable),
                writable=tuple(writable),
                immutable=tuple(immutable),
            ),
            resources=ResourceCeiling(
                max_nodes=max_nodes,
                max_gpus=max_gpus,
                max_walltime_minutes=max_walltime_minutes,
                max_jobs=max_jobs,
            ),
            egress=EgressPolicy(allowed_sinks=frozenset(allowed_sinks)),
        )
