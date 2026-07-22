"""``TaskScopeExecutor`` -- the A4 task-scope-enforcement defense.

This is the integration the whole benchmark hinges on (development-plan §3.2,
§5.2, §6): a pipeline element that enforces ``taskbound_core.PolicyEngine`` at
runtime by **wrapping** AgentDojo's ``ToolsExecutor`` *by composition* rather
than forking it. It gates the tool calls the agent requested against the
``TaskPolicy``, delegates the allowed subset to the inner ``ToolsExecutor`` for
execution, and synthesizes tool-result messages denying the rest.

Because the same ``taskbound_core.evaluate`` powers both this defense and the
offline scoring oracle, "what the defense blocks" and "what the oracle counts as
a violation" cannot drift apart.
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

from taskbound_core import (
    Action,
    Decision,
    EnvironmentState,
    TaskPolicy,
    evaluate,
)

__all__ = ["ActionMapper", "EnvAdapter", "TaskScopeExecutor"]


class ActionMapper(Protocol):
    """Maps one requested tool call to a ``taskbound_core.Action`` to be judged.

    Return ``None`` for a tool call that is not policy-governed (always allowed
    through). In the full bench this is attached per tool; a plain callable or
    dict-backed mapper is enough for a suite.
    """

    def __call__(self, tool_call: FunctionCall) -> Optional[Action]: ...


# Derives the taskbound-core view of the world (path->project, canaries, shared
# paths) from AgentDojo's live environment, so the pure engine can judge actions.
EnvAdapter = Callable[[Env], EnvironmentState]


class TaskScopeExecutor(BasePipelineElement):
    """Wraps a ``ToolsExecutor`` and denies out-of-scope tool calls.

    Args:
        policy: the declared scope of the current task.
        mapper: turns a requested ``FunctionCall`` into an ``Action`` to judge
            (or ``None`` to pass it through ungoverned).
        inner: the ``ToolsExecutor`` that actually runs allowed calls. A default
            one is created if not supplied.
        env_adapter: derives an ``EnvironmentState`` from the live AgentDojo env.
    """

    name = "task_scope_executor"

    def __init__(
        self,
        policy: TaskPolicy,
        mapper: ActionMapper,
        inner: Optional[ToolsExecutor] = None,
        env_adapter: Optional[EnvAdapter] = None,
    ) -> None:
        self.policy = policy
        self.mapper = mapper
        self.inner = inner if inner is not None else ToolsExecutor()
        self.env_adapter = env_adapter

    def _denial_message(self, tool_call: FunctionCall, decision: Decision) -> ChatToolResultMessage:
        return ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("")],
            tool_call_id=tool_call.id,
            tool_call=tool_call,
            error=(
                f"PolicyDenied: action outside the scope of task "
                f"'{self.policy.task_id}'. {decision.reason}"
            ),
        )

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        # Only gate when the last message actually requests tool calls; otherwise
        # behave exactly like the inner executor (same early-out contract).
        if len(messages) == 0 or messages[-1]["role"] != "assistant":
            return self.inner.query(query, runtime, env, messages, extra_args)
        tool_calls = messages[-1].get("tool_calls")
        if not tool_calls:
            return self.inner.query(query, runtime, env, messages, extra_args)

        tb_env = self.env_adapter(env) if self.env_adapter is not None else EnvironmentState()

        # Judge every requested call, preserving original order.
        allowed: list[FunctionCall] = []
        # verdicts[i] is None if allowed, else the denial Decision for tool_calls[i].
        verdicts: list[Optional[Decision]] = []
        for tool_call in tool_calls:
            action = self.mapper(tool_call)
            if action is None:
                allowed.append(tool_call)
                verdicts.append(None)
                continue
            decision = evaluate(action, self.policy, tb_env)
            if decision.allowed:
                allowed.append(tool_call)
                verdicts.append(None)
            else:
                verdicts.append(decision)

        # Fast path: nothing denied -> pure delegation, identical behavior.
        if all(v is None for v in verdicts):
            return self.inner.query(query, runtime, env, messages, extra_args)

        # Delegate execution of the allowed subset to the real ToolsExecutor by
        # handing it a copy of the assistant message carrying only allowed calls.
        filtered_last = dict(messages[-1])
        filtered_last["tool_calls"] = allowed
        inner_input = [*messages[:-1], filtered_last]
        query, runtime, env, inner_out, extra_args = self.inner.query(
            query, runtime, env, inner_input, extra_args
        )
        allowed_results = list(inner_out[len(inner_input):])

        # Reassemble tool results in the ORIGINAL order and restore the original
        # assistant message, so the trace faithfully shows every requested call
        # (including the denied ones) alongside its outcome.
        merged: list[ChatMessage] = []
        allowed_iter = iter(allowed_results)
        for tool_call, decision in zip(tool_calls, verdicts):
            if decision is None:
                merged.append(next(allowed_iter))
            else:
                merged.append(self._denial_message(tool_call, decision))

        final_messages = [*messages, *merged]
        return query, runtime, env, final_messages, extra_args
