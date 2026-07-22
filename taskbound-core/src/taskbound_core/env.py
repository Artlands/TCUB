"""``EnvironmentState`` -- the read-only facts the engine needs to judge an action.

Kept deliberately small and pure: it answers "which project owns this path?",
"is this path durable/shared?", and "does this text carry a canary?" -- the
ground the ``PolicyEngine`` stands on without doing any I/O itself. Both the
in-memory bench and the real-cluster harness populate one of these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

from .glob import path_matches

__all__ = ["EnvironmentState"]


@dataclass(frozen=True)
class EnvironmentState:
    """Facts about the world at the moment an action is judged.

    - ``path_project``: glob -> owning project. Longest matching glob wins, so
      more specific declarations override broader ones.
    - ``shared_globs``: paths whose writes survive job teardown (shared scratch,
      collaboration space) -- the substrate of ``shared_fs_persistence``.
    - ``canaries``: unique token -> the out-of-scope location it guards. A canary
      appearing in egressed text is the leak signal (never real exfiltration).
    - ``immutable_hashes``: declared-immutable artifact -> pre-run hash, for
      snapshot/diff detection of ``integrity_tampering`` by downstream tooling.
    """

    path_project: Mapping[str, str] = field(default_factory=dict)
    shared_globs: tuple[str, ...] = ()
    canaries: Mapping[str, str] = field(default_factory=dict)
    immutable_hashes: Mapping[str, str] = field(default_factory=dict)

    def project_of(self, path: Optional[str]) -> Optional[str]:
        if path is None:
            return None
        best: Optional[str] = None
        best_len = -1
        for pattern, project in self.path_project.items():
            if len(pattern) > best_len and path_matches(path, pattern):
                best, best_len = project, len(pattern)
        return best

    def is_shared(self, path: Optional[str]) -> bool:
        if path is None:
            return False
        return any(path_matches(path, g) for g in self.shared_globs)

    def canary_in(self, text: str) -> Optional[str]:
        for token in self.canaries:
            if token and token in text:
                return token
        return None
