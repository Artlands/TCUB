# M1 de-risk decision: TaskScopeExecutor wraps ToolsExecutor by composition

**Question (plan §3.2, the #1 technical risk):** can `TaskScopeExecutor` cleanly
wrap AgentDojo's `ToolsExecutor` *by composition*, or must we fork that class?

**Decision: composition works. No fork.** `TaskScopeExecutor` holds an inner
`ToolsExecutor` and delegates execution to it. AgentDojo pinned at `0.1.35`.

## Why composition is clean here

AgentDojo's pipeline contract is a single method:

```python
query(query, runtime, env, messages, extra_args)
    -> (query, runtime, env, messages, extra_args)
```

and `ToolsExecutor` executes exactly `messages[-1]["tool_calls"]`, appending one
`ChatToolResultMessage` per call. That gives us three properties we exploit:

1. **The gate point is data, not control flow.** The pending tool calls live in
   the last assistant message. We judge them with `taskbound_core.evaluate`
   *before* delegating, so we never need to reach inside `ToolsExecutor`'s loop.
2. **The allowed subset is delegable.** We hand the inner executor a copy of the
   assistant message carrying only the allowed calls; it runs them with its real
   logic (arg coercion, `runtime.run_function`, output formatting). We add no
   execution code of our own — zero duplication of the thing we're wrapping.
3. **Denials are synthesizable in the same shape.** A denied call becomes a
   `ChatToolResultMessage` with `error="PolicyDenied: ..."`, identical in type to
   what the executor emits, so downstream elements and the trace are unaffected.
   We restore the original assistant message and re-interleave results in the
   requested order, so the trace faithfully records every requested call.

No private attributes, no monkeypatching, no subclass override of internals are
required — only the public `query` contract and the public message/`FunctionCall`
types. That is what makes it fork-free and robust to AgentDojo point releases.

## Evidence (`tests/test_taskscope_executor.py`, 5/5 green)

A toy HPC suite (a `TaskEnvironment` + `read_file`/`submit_job` tools + a
`FunctionsRuntime`), no LLM calls:

- **control** — a bare `ToolsExecutor` on the same input *executes the attack*
  (reads `/projects/projB/secret.dat`, submits a 64-node job): establishes that
  the wrapper is what blocks it, not the suite.
- **block** — the wrapped executor runs only the in-scope read; the cross-project
  read and the over-ceiling submit never touch the environment.
- **fidelity** — results come back in the original order, the assistant history
  keeps all three requested calls, denials carry `PolicyDenied` + the reason.
- **transparency** — with an all-allowed policy, behavior is identical to the
  bare `ToolsExecutor`.

## Consequences for later milestones

- The fork-fallback branch in the risk table (plan §12) is **closed**; no tracked
  fork of `ToolsExecutor` is needed.
- Remaining bench work (M3+) is the in-memory HPC `TaskEnvironment`s, the per-tool
  `ActionMapper`s, and the `EnvAdapter` that derives `EnvironmentState`
  (path→project, canaries, shared paths) from a live env — not the pipeline
  integration, which is done.
- The same `taskbound_core.evaluate` used here is the offline oracle, so the A4
  defense and the scoring oracle are one code path by construction.
