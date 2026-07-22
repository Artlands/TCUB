"""The two seams between AgentDojo and taskbound-core for the HPC suite:

- ``hpc_action_mapper`` -- a requested ``FunctionCall`` -> a ``taskbound_core.Action``
  the policy engine can judge (``None`` for ungoverned calls).
- ``hpc_env_adapter`` -- a live ``HPCEnv`` -> the pure ``EnvironmentState`` the
  engine and oracle read (path->project, shared globs, canaries, immutable hashes).

The same two are used by the runtime A4 defense (``TaskScopeExecutor``) and by the
offline scoring in ``benchmark.py``, so defense and scoring never disagree.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from agentdojo.functions_runtime import FunctionCall

from taskbound_core import Action, ActionType, EnvironmentState, path_matches

from .env import HPCEnv

__all__ = ["hpc_action_mapper", "hpc_env_adapter"]


def hpc_action_mapper(tool_call: FunctionCall) -> Optional[Action]:
    fn = tool_call.function
    args = tool_call.args
    if fn == "read_file":
        return Action(ActionType.READ, path=str(args["path"]))
    if fn == "write_file":
        return Action(ActionType.WRITE, path=str(args["path"]), payload=str(args.get("content", "")))
    if fn == "edit_file":
        return Action(ActionType.EDIT, path=str(args["path"]), payload=str(args.get("content", "")))
    if fn == "submit_job":
        return Action(ActionType.SUBMIT_JOB, nodes=int(args["nodes"]))
    return None


def hpc_env_adapter(env: HPCEnv) -> EnvironmentState:
    immutable_hashes = {
        path: hashlib.sha256(content.encode()).hexdigest()
        for path, content in env.files.items()
        if any(path_matches(path, g) for g in env.immutable_globs)
    }
    return EnvironmentState(
        path_project=dict(env.file_projects),
        shared_globs=tuple(env.shared_globs),
        canaries=dict(env.canaries),
        immutable_hashes=immutable_hashes,
    )
