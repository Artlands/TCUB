"""Gating pipeline elements: enforcing defenses that wrap AgentDojo's
``ToolsExecutor`` by composition (no fork).

``GatingExecutor`` is the shared machinery (development-plan §3.2, §5.2): for each
requested tool call it asks a ``_judge`` whether to allow it, delegates the
allowed subset to an inner executor for real execution, and synthesizes denial
tool-results for the rest -- in original order, with the assistant history
preserved. Because gates nest (each wraps an inner executor), the defense matrix
(A2 allowlist, A3 egress gate, A4 task-scope) composes by stacking.

``TaskScopeExecutor`` (A4) enforces ``taskbound_core.evaluate`` -- the *same*
function the offline oracle replays -- so "what the defense blocks" and "what the
oracle counts as a violation" cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Callable, Optional, Protocol

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionCall, FunctionsRuntime
from agentdojo.types import (
    ChatMessage,
    ChatToolResultMessage,
    text_content_block_from_string,
)

from taskbound_core import Action, EnvironmentState, TaskPolicy, evaluate

__all__ = [
    "ActionMapper",
    "EnvAdapter",
    "GatingExecutor",
    "TaskScopeExecutor",
    "ToolAllowlistExecutor",
    "EgressGateExecutor",
]


class ActionMapper(Protocol):
    def __call__(self, tool_call: FunctionCall) -> Optional[Action]: ...


EnvAdapter = Callable[[Env], EnvironmentState]


class GatingExecutor(BasePipelineElement):
    """Base gate: judge each requested tool call, execute the allowed subset via
    an inner executor, deny the rest. Subclasses implement ``_judge``."""

    name = "gating_executor"

    def __init__(self, inner: Optional[BasePipelineElement] = None) -> None:
        self.inner = inner if inner is not None else ToolsExecutor()

    def _judge(self, tool_call: FunctionCall, env: Env) -> Optional[str]:
        """Return ``None`` to allow, or an error string to deny the call."""
        raise NotImplementedError

    def _denial_message(self, tool_call: FunctionCall, reason: str) -> ChatToolResultMessage:
        return ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("")],
            tool_call_id=tool_call.id,
            tool_call=tool_call,
            error=reason,
        )

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        if len(messages) == 0 or messages[-1]["role"] != "assistant":
            return self.inner.query(query, runtime, env, messages, extra_args)
        tool_calls = messages[-1].get("tool_calls")
        if not tool_calls:
            return self.inner.query(query, runtime, env, messages, extra_args)

        allowed: list[FunctionCall] = []
        reasons: list[Optional[str]] = []
        for tool_call in tool_calls:
            reason = self._judge(tool_call, env)
            reasons.append(reason)
            if reason is None:
                allowed.append(tool_call)

        if all(r is None for r in reasons):
            return self.inner.query(query, runtime, env, messages, extra_args)

        filtered_last = dict(messages[-1])
        filtered_last["tool_calls"] = allowed
        inner_input = [*messages[:-1], filtered_last]
        query, runtime, env, inner_out, extra_args = self.inner.query(
            query, runtime, env, inner_input, extra_args
        )
        allowed_results = iter(inner_out[len(inner_input):])

        merged: list[ChatMessage] = []
        for tool_call, reason in zip(tool_calls, reasons):
            if reason is None:
                merged.append(next(allowed_results))
            else:
                merged.append(self._denial_message(tool_call, reason))

        return query, runtime, env, [*messages, *merged], extra_args


class TaskScopeExecutor(GatingExecutor):
    """A4 -- deny any tool call whose action is outside the task's ``TaskPolicy``."""

    name = "task_scope_executor"

    def __init__(
        self,
        policy: TaskPolicy,
        mapper: ActionMapper,
        inner: Optional[BasePipelineElement] = None,
        env_adapter: Optional[EnvAdapter] = None,
    ) -> None:
        super().__init__(inner)
        self.policy = policy
        self.mapper = mapper
        self.env_adapter = env_adapter

    def _judge(self, tool_call: FunctionCall, env: Env) -> Optional[str]:
        action = self.mapper(tool_call)
        if action is None:
            return None
        tb_env = self.env_adapter(env) if self.env_adapter is not None else EnvironmentState()
        decision = evaluate(action, self.policy, tb_env)
        if decision.allowed:
            return None
        return (
            f"PolicyDenied: action outside the scope of task "
            f"'{self.policy.task_id}'. {decision.reason}"
        )


class ToolAllowlistExecutor(GatingExecutor):
    """A2 -- deny any tool call whose function is not on the vetted allowlist
    (development-plan §6; the Shi et al. tool-description attack surface)."""

    name = "tool_allowlist_executor"

    def __init__(self, allowed_tools, inner: Optional[BasePipelineElement] = None) -> None:
        super().__init__(inner)
        self.allowed_tools = frozenset(allowed_tools)

    def _judge(self, tool_call: FunctionCall, env: Env) -> Optional[str]:
        if tool_call.function in self.allowed_tools:
            return None
        return f"ToolNotAllowed: '{tool_call.function}' is not on the task's tool allowlist."


class EgressGateExecutor(GatingExecutor):
    """A3 -- block egress calls carrying an out-of-scope canary (development-plan
    §6 egress control). Inert on scenarios with no egress action."""

    name = "egress_gate_executor"

    def __init__(
        self,
        mapper: ActionMapper,
        env_adapter: EnvAdapter,
        inner: Optional[BasePipelineElement] = None,
    ) -> None:
        super().__init__(inner)
        self.mapper = mapper
        self.env_adapter = env_adapter

    def _judge(self, tool_call: FunctionCall, env: Env) -> Optional[str]:
        action = self.mapper(tool_call)
        if action is None:
            return None
        tb_env = self.env_adapter(env)
        token = tb_env.canary_in(action.payload)
        if token is not None:
            return f"EgressBlocked: payload carries out-of-scope canary {token!r}."
        return None
