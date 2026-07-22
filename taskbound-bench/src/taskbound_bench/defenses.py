"""The defense matrix (development-plan §6): A0-A4 and the A1+A4 / A2+A4 combos,
each expressed as composable pipeline elements dropped into the tool loop.

Controls split into two kinds:

- **enforcing** gates (A2 allowlist, A3 egress, A4 task-scope) block a call
  before it executes -- they nest as ``GatingExecutor``s around the base
  ``ToolsExecutor``, so combinations just stack.
- **advisory** elements (A1 provenance labeling) annotate what the model sees but
  do not block. Against a maximally-susceptible agent (the deterministic
  ``ScriptedLLM``) advisory controls do not reduce ASR -- the matrix reports that
  honestly; their value surfaces with a real model driver (M5 axes).

The whole point of the joint metric: only task-scope enforcement (A4) reduces ASR
for these HPC-native, authorized-tool consequences, and it *composes* with the
cheaper transferable defenses rather than replacing them.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import ChatMessage

from .executor import (
    EgressGateExecutor,
    TaskScopeExecutor,
    ToolAllowlistExecutor,
)
from .mapping import hpc_action_mapper, hpc_env_adapter

__all__ = ["Control", "Defense", "ProvenanceLabeler", "build_loop_elements"]


class Control(Enum):
    PROVENANCE = "provenance"  # A1 (advisory)
    ALLOWLIST = "allowlist"    # A2 (enforcing)
    EGRESS_GATE = "egress"     # A3 (enforcing)
    TASK_SCOPE = "task_scope"  # A4 (enforcing)


class Defense(Enum):
    A0 = ()
    A1 = (Control.PROVENANCE,)
    A2 = (Control.ALLOWLIST,)
    A3 = (Control.EGRESS_GATE,)
    A4 = (Control.TASK_SCOPE,)
    A1_A4 = (Control.PROVENANCE, Control.TASK_SCOPE)
    A2_A4 = (Control.ALLOWLIST, Control.TASK_SCOPE)

    @property
    def controls(self) -> tuple[Control, ...]:
        return self.value

    @property
    def label(self) -> str:
        return self.name.replace("_", "+")


class ProvenanceLabeler(BasePipelineElement):
    """A1 -- prepend a trust/source label to each fresh tool-output message so the
    model can condition on provenance (development-plan §7.1). Advisory only."""

    name = "provenance_labeler"
    _MARK = "⟦prov"

    def __init__(self, policy, mapper=hpc_action_mapper, env_adapter=hpc_env_adapter) -> None:
        self.policy = policy
        self.mapper = mapper
        self.env_adapter = env_adapter

    def _label_for(self, tool_call, env) -> str:
        action = self.mapper(tool_call) if tool_call is not None else None
        if action is None or action.path is None:
            return f"{self._MARK}: trusted⟧ "
        project = self.env_adapter(env).project_of(action.path)
        in_scope = (not self.policy.projects) or (project in self.policy.projects)
        tag = "trusted" if in_scope else f"UNTRUSTED source={project}"
        return f"{self._MARK}: {tag}⟧ "

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        labeled = list(messages)
        for i, message in enumerate(labeled):
            if message.get("role") != "tool":
                continue
            content = message.get("content") or []
            if not content or content[0].get("content", "").startswith(self._MARK):
                continue
            label = self._label_for(message.get("tool_call"), env)
            new_message = dict(message)
            new_first = dict(content[0])
            new_first["content"] = label + new_first.get("content", "")
            new_message["content"] = [new_first, *content[1:]]
            labeled[i] = new_message
        return query, runtime, env, labeled, extra_args


def build_loop_elements(scenario, defense: Defense) -> list[BasePipelineElement]:
    """Build the tool-loop elements for a defense: a (possibly nested) executor
    followed by any advisory elements."""
    controls = set(defense.controls)

    executor: BasePipelineElement = ToolsExecutor()
    if Control.EGRESS_GATE in controls:
        executor = EgressGateExecutor(hpc_action_mapper, hpc_env_adapter, inner=executor)
    if Control.TASK_SCOPE in controls:
        executor = TaskScopeExecutor(
            scenario.policy, hpc_action_mapper, inner=executor, env_adapter=hpc_env_adapter
        )
    if Control.ALLOWLIST in controls:
        executor = ToolAllowlistExecutor(scenario.allowed_tools(), inner=executor)

    elements: list[BasePipelineElement] = [executor]
    if Control.PROVENANCE in controls:
        elements.append(ProvenanceLabeler(scenario.policy))
    return elements
