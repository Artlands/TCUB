"""taskbound-bench -- the AgentDojo consumer of taskbound-core.

Hosts the in-memory scored matrix and the ``TaskScopeExecutor`` (A4 defense),
which enforces the shared ``taskbound_core.PolicyEngine`` inside AgentDojo's
agent pipeline. Depends on AgentDojo (pinned) and taskbound-core.
"""

from __future__ import annotations

from .executor import ActionMapper, EnvAdapter, TaskScopeExecutor

__version__ = "0.1.0"

__all__ = ["__version__", "TaskScopeExecutor", "ActionMapper", "EnvAdapter"]
