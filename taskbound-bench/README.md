# taskbound-bench

The **AgentDojo consumer** of [`taskbound-core`](../taskbound-core). It hosts the
in-memory scored matrix and the **`TaskScopeExecutor`** — the A4
task-scope-enforcement defense that enforces the shared `taskbound_core.PolicyEngine`
inside AgentDojo's agent pipeline.

Unlike `taskbound-core` (stdlib only) and `taskbound-harness` (stdlib only), this
package **depends on AgentDojo**, pinned to an exact version (`agentdojo==0.1.35`)
and never vendored. AgentDojo pins Python `<3.13`, so this package requires
`>=3.10,<3.13`.

## Status

- **M1 (de-risk) — done.** `TaskScopeExecutor` wraps AgentDojo's `ToolsExecutor`
  **by composition, no fork**. See [`M1_FINDINGS.md`](./M1_FINDINGS.md).
- M3+ (in-memory HPC `TaskEnvironment`s, per-tool `ActionMapper`s, `EnvAdapter`,
  full scored matrix) — not yet built.

## `TaskScopeExecutor`

A `BasePipelineElement` that, for each tool call the agent requests:

1. maps it to a `taskbound_core.Action` (via an `ActionMapper`),
2. judges it with `taskbound_core.evaluate` against the task's `TaskPolicy`,
3. delegates the **allowed** calls to an inner `ToolsExecutor` for real execution,
4. returns `PolicyDenied` tool-results for the rest — in original order, with the
   assistant history preserved.

```python
from taskbound_bench import TaskScopeExecutor
from taskbound_core import TaskPolicy

executor = TaskScopeExecutor(
    policy=TaskPolicy.build("job-42", projects=["projA"],
                            readable=["/projects/projA/**"], max_nodes=4),
    mapper=my_tool_to_action_mapper,   # FunctionCall -> Action | None
    env_adapter=my_env_adapter,        # AgentDojo Env -> taskbound_core.EnvironmentState
)
# drop `executor` into a ToolsExecutionLoop in place of a bare ToolsExecutor.
```

## Develop / test

Uses [uv](https://docs.astral.sh/uv/) to pull a compatible Python and pin deps:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ../taskbound-core -e '.[test]'
.venv/bin/python -m pytest tests/ -v
```
