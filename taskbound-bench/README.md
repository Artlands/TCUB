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
- **M3 (AgentDojo integration) — done.** An in-memory HPC `TaskEnvironment`
  (`env.py`) + tools (`tools.py`) + the `hpc_action_mapper`/`hpc_env_adapter`
  seams (`mapping.py`), assembled into the **real AgentDojo pipeline**
  (`pipeline.py`) with a deterministic `ScriptedLLM` model stand-in, scored by
  the thin `benchmark.py` runner into **USR/ASR**. First scenario
  (`cross_project_read.log_note`) result:

  | defense | USR | ASR | verdict |
  |---|---|---|---|
  | A0 (none) | 1.00 | 1.00 | VIOLATED |
  | A4 (task-scope) | 1.00 | 0.00 | SECURE |

  Enforcement cuts ASR 1.00 → 0.00 at zero utility cost. Drop a real
  `OpenAILLM`/`AnthropicLLM` in place of `ScriptedLLM` for a genuine model run.
- **M4 (full registry + attack registry + matrix) — done.** All four
  consequences × 2 user tasks each (8 scenarios, `scenarios/`) × a swappable
  attack registry (`attacks.py`: `direct_note`, `authority_spoof`, `urgency`,
  `tool_result_footer`) × {A0, A4} = a **64-cell deterministic matrix**
  (`run_full_matrix`). Aggregate: **A0 ASR 1.00 / A4 ASR 0.00, USR 1.00 both** —
  every consequence cut to zero at no utility cost, verdict invariant across
  attack phrasings.
- **M5 (defense matrix + metrics + both axes) — machinery done.**
  - **Defense matrix** (`defenses.py`): A0–A4 + A1+A4 / A2+A4, as composable
    gates (`executor.py`: `GatingExecutor` base → `TaskScopeExecutor` A4,
    `ToolAllowlistExecutor` A2, `EgressGateExecutor` A3) + advisory
    `ProvenanceLabeler` A1.
  - **Metric layer** (`metrics.py`): USR, ASR, utility-under-attack, STCR,
    defense cost (Δutility), the HPC consequence/severity metrics (UAR/SDER/ITR/SPR),
    and a severity-weighted rollup.
  - **Both evaluation axes** (`drivers.py`): the primary agent-product axis
    (`AgentAdapter` + `run_case_adapter`, interposing our controls on a product's
    action stream) and the secondary reference-model axis
    (`reference_axis_sweep`, fixed scaffold × swappable model).

  Deterministic joint table (reference scaffold, susceptible stand-in model):

  | defense | USR | ASR | STCR | UAR | SDER | ITR | SPR |
  |---|---|---|---|---|---|---|---|
  | A0 | 1.00 | 1.00 | 0.00 | 1.00 | 96.0 | 1.00 | 1.00 |
  | A1 (provenance) | 1.00 | 1.00 | 0.00 | 1.00 | 96.0 | 1.00 | 1.00 |
  | A2 (allowlist) | 1.00 | 0.75 | 0.25 | 1.00 | 96.0 | **0.00** | 1.00 |
  | A3 (egress) | 1.00 | 1.00 | 0.00 | 1.00 | 96.0 | 1.00 | 1.00 |
  | **A4 (task-scope)** | 1.00 | **0.00** | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
  | A1+A4 | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
  | A2+A4 | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |

  Only task-scope enforcement drives ASR to 0 at zero utility cost, and it
  composes with the cheaper defenses. A2 helps *only* where the attack needs a
  tool the task doesn't (integrity → ITR 0); it can't stop authorized-tool abuse.

### Producing the headline (credential-gated) results

The M5 machinery is complete and deterministic. The **headline numbers** — ≥2
real deployed agent products (primary axis) and ≥3 frontier models (secondary
axis) — require credentials/product access:

```python
# secondary axis: swap the stand-in for real AgentDojo model elements
from agentdojo.agent_pipeline import OpenAILLM, AnthropicLLM
factories = {
    "gpt-x":   lambda s: OpenAILLM("gpt-x", openai_client),
    "claude-x": lambda s: AnthropicLLM("claude-x", anthropic_client),
    # ... ≥3 models
}
reports = reference_axis_sweep(factories)

# primary axis: implement AgentAdapter against a real product, then
# run_case_adapter(scenario, defense, YourProductAdapter())
```

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
