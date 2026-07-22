"""HPC tools the agent can call, registered into an AgentDojo ``FunctionsRuntime``.

These are ordinary AgentDojo tools (schema derived from type hints + docstrings);
they mutate the live ``HPCEnv``. ``mapping.hpc_action_mapper`` translates a
requested call into a ``taskbound_core.Action`` for the policy engine/oracle.
"""

from __future__ import annotations

from typing import Annotated

from agentdojo.functions_runtime import Depends

from .env import HPCEnv

__all__ = ["read_file", "write_file", "edit_file", "submit_job", "HPC_TOOLS", "register_hpc_tools"]

_Env = Annotated[HPCEnv, Depends(lambda env: env)]


def read_file(path: str, env: _Env) -> str:
    """Read a file from the HPC filesystem.

    :param path: absolute path of the file to read.
    """
    return env.files.get(path, "")


def write_file(path: str, content: str, env: _Env) -> str:
    """Create or overwrite a file.

    :param path: absolute path to write.
    :param content: text to write.
    """
    env.files[path] = content
    env.writes.append(path)
    return f"wrote {path}"


def edit_file(path: str, content: str, env: _Env) -> str:
    """Modify an existing file in place.

    :param path: absolute path to edit.
    :param content: new full contents.
    """
    env.files[path] = content
    env.writes.append(path)
    return f"edited {path}"


def submit_job(nodes: int, env: _Env) -> str:
    """Submit a Slurm job.

    :param nodes: number of nodes to request.
    """
    job_id = f"job-{len(env.jobs) + 1}"
    env.jobs.append({"id": job_id, "nodes": nodes})
    return job_id


HPC_TOOLS = [read_file, write_file, edit_file, submit_job]


def register_hpc_tools(runtime) -> None:
    for tool in HPC_TOOLS:
        runtime.register_function(tool)
