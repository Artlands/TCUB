"""Cluster adapters: where actions actually run.

- ``StubCluster`` -- in-memory, deterministic. This is what M2 and all
  deterministic scoring use; it never touches real infrastructure.
- ``SlurmClusterAdapter`` -- the real path (drives real ``sbatch`` + a sandboxed
  filesystem). It is the permanent real-Slurm validation adapter; M2 ships its
  skeleton "behind a stub" and it is exercised at M6/M7 on the controlled
  cluster. Its filesystem ops are real (and testable in a tmpdir); job
  submission shells out to ``sbatch``.

Both satisfy the same ``ClusterAdapter`` protocol, so the runner is adapter-blind.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Protocol

from taskbound_core import Action, ActionType

from .types import Observation

__all__ = ["ClusterAdapter", "StubCluster", "SlurmClusterAdapter"]


class ClusterAdapter(Protocol):
    def execute(self, action: Action) -> Observation: ...


class StubCluster:
    """Deterministic in-memory cluster. Records every effect for inspection."""

    def __init__(self, seed) -> None:
        # `seed` is a scenario.ClusterSeed; only .files is needed at runtime.
        self.files: dict[str, str] = dict(getattr(seed, "files", {}) or {})
        self.jobs: list[dict] = []
        self.egress_log: list[tuple[Optional[str], str]] = []
        self.writes: list[str] = []

    def execute(self, action: Action) -> Observation:
        t = action.type
        if t is ActionType.READ:
            return Observation(True, content=self.files.get(action.path or "", ""))
        if t in (ActionType.WRITE, ActionType.EDIT):
            path = action.path or ""
            self.files[path] = action.payload if action.payload else self.files.get(path, "")
            self.writes.append(path)
            return Observation(True)
        if t is ActionType.SUBMIT_JOB:
            job_id = f"job-{len(self.jobs) + 1}"
            self.jobs.append(
                {
                    "id": job_id,
                    "nodes": action.nodes,
                    "gpus": action.gpus,
                    "walltime_minutes": action.walltime_minutes,
                    "jobs": action.jobs,
                }
            )
            return Observation(True, content=job_id)
        if t is ActionType.EGRESS:
            self.egress_log.append((action.sink, action.payload))
            return Observation(True)
        return Observation(False, error=f"unhandled action type {t!r}")  # pragma: no cover


class SandboxViolation(RuntimeError):
    """Kill-switch (plan §8.4): an action tried to leave the test sandbox."""


class SlurmClusterAdapter:
    """Real-cluster adapter. Not exercised in CI; used on the controlled cluster.

    All filesystem access is confined to ``sandbox_root`` by a kill-switch that
    fires independently of the agent's or oracle's logic.
    """

    def __init__(self, sandbox_root: str, *, partition: Optional[str] = None) -> None:
        self.sandbox_root = Path(sandbox_root).resolve()
        self.partition = partition
        self.jobs: list[str] = []

    def _safe_path(self, path: Optional[str]) -> Path:
        p = (self.sandbox_root / (path or "").lstrip("/")).resolve()
        if self.sandbox_root not in p.parents and p != self.sandbox_root:
            raise SandboxViolation(f"path {path!r} escapes sandbox {self.sandbox_root}")
        return p

    def execute(self, action: Action) -> Observation:
        t = action.type
        if t is ActionType.READ:
            p = self._safe_path(action.path)
            return Observation(True, content=p.read_text() if p.exists() else "")
        if t in (ActionType.WRITE, ActionType.EDIT):
            p = self._safe_path(action.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(action.payload or "")
            return Observation(True)
        if t is ActionType.SUBMIT_JOB:
            return self._sbatch(action)
        if t is ActionType.EGRESS:
            # Real egress goes only to the controlled canary sink; wired at M6/M7.
            raise NotImplementedError("egress adapter is wired during real-cluster bring-up")
        return Observation(False, error=f"unhandled action type {t!r}")

    def _sbatch(self, action: Action) -> Observation:  # pragma: no cover - needs real Slurm
        cmd = ["sbatch", "--parsable", f"--nodes={action.nodes}"]
        if self.partition:
            cmd.append(f"--partition={self.partition}")
        if action.walltime_minutes:
            cmd.append(f"--time={action.walltime_minutes}")
        script = self._safe_path("job.sbatch")
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("#!/bin/bash\nsrun hostname\n")
        cmd.append(str(script))
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.sandbox_root)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return Observation(False, error=f"sbatch failed: {e}")
        job_id = out.stdout.strip()
        self.jobs.append(job_id)
        return Observation(True, content=job_id)
