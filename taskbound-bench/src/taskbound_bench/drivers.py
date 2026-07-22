"""The two evaluation axes (development-plan §3.1, §9).

- **Reference axis (secondary)** -- ``reference_axis_sweep``: hold the scaffold
  (``build_pipeline``) fixed and vary the model. A model is any AgentDojo LLM
  element (``OpenAILLM``/``AnthropicLLM``/...); pass a factory per model id. This
  decomposes a product's susceptibility into model vs. scaffold and anchors to a
  bare-model baseline (mirrors AgentDojo). Credential-gated for real models; the
  deterministic ``ScriptedLLM`` stands in for tests.

- **Primary axis** -- ``AgentAdapter`` + ``run_case_adapter``: evaluate a real
  deployed agent *product* as deployed. The product proposes actions; we interpose
  the SAME enforcing controls (``taskbound_core.evaluate`` for A4, the allowlist,
  the egress gate) between its actions and the environment, so A1-A4 measure what
  our task-scoped controls add *on top of* a hardened product. A real product is
  wired by implementing ``AgentAdapter``; ``FakeAgentAdapter`` is the test double.
"""

from __future__ import annotations

from typing import Callable, Mapping, Optional, Protocol, Sequence

from agentdojo.agent_pipeline import BasePipelineElement

from taskbound_core import Action, ActionType, evaluate, security_oracle

from .attacks import DEFAULT_ATTACK, Attack
from .benchmark import CaseResult, MatrixReport, materialize_env, run_case
from .defenses import Control, Defense
from .env import HPCEnv
from .mapping import hpc_action_mapper, hpc_env_adapter
from .scenario import BenchScenario
from .scenarios import all_scenarios

__all__ = [
    "reference_axis_sweep",
    "apply_action",
    "AgentAdapter",
    "FakeAgentAdapter",
    "run_case_adapter",
]

# --- reference (model) axis --------------------------------------------------

# A model factory yields a *fresh* LLM element for a scenario (real models are
# stateful; a fresh element per case is required).
ModelFactory = Callable[[BenchScenario], BasePipelineElement]


def reference_axis_sweep(
    model_factories: Mapping[str, ModelFactory],
    *,
    defenses: Optional[Sequence[Defense]] = None,
    scenarios: Optional[Sequence[BenchScenario]] = None,
    attack: Attack = DEFAULT_ATTACK,
) -> dict[str, MatrixReport]:
    """Sweep {model_id -> matrix report} on the fixed reference scaffold."""
    defenses = defenses if defenses is not None else list(Defense)
    scenarios = scenarios if scenarios is not None else all_scenarios()
    reports: dict[str, MatrixReport] = {}
    for model_id, factory in model_factories.items():
        cells = [
            run_case(scenario, defense, attack, llm=factory(scenario))
            for scenario in scenarios
            for defense in defenses
        ]
        reports[model_id] = MatrixReport(cells=tuple(cells))
    return reports


# --- primary (agent-product) axis --------------------------------------------

_ACTION_TOOL = {
    ActionType.READ: "read_file",
    ActionType.WRITE: "write_file",
    ActionType.EDIT: "edit_file",
    ActionType.SUBMIT_JOB: "submit_job",
}


def apply_action(env: HPCEnv, action: Action) -> str:
    """Apply one action's effect to the in-memory env; return an observation."""
    t = action.type
    if t is ActionType.READ:
        return env.files.get(action.path or "", "")
    if t in (ActionType.WRITE, ActionType.EDIT):
        env.files[action.path or ""] = action.payload or ""
        env.writes.append(action.path or "")
        return "ok"
    if t is ActionType.SUBMIT_JOB:
        env.jobs.append({"id": f"job-{len(env.jobs) + 1}", "nodes": action.nodes})
        return "submitted"
    if t is ActionType.EGRESS:
        env.egress_log.append({"sink": action.sink, "payload": action.payload})
        return "sent"
    return ""


class AgentAdapter(Protocol):
    """A real deployed agent product, normalized to our action stream."""

    def reset(self, scenario: BenchScenario) -> None: ...
    def propose(self, observation: Optional[str]) -> Optional[Action]: ...


class FakeAgentAdapter:
    """Deterministic product stand-in: replays a fixed action list."""

    def __init__(self, actions: Sequence[Action]) -> None:
        self._actions = list(actions)
        self._i = 0

    @classmethod
    def from_scenario(cls, scenario: BenchScenario, *, susceptible: bool = True) -> "FakeAgentAdapter":
        script = scenario.susceptible_script() if susceptible else scenario.robust_script()
        actions = [a for a in (hpc_action_mapper(fc) for fc in script) if a is not None]
        return cls(actions)

    def reset(self, scenario: BenchScenario) -> None:
        self._i = 0

    def propose(self, observation: Optional[str]) -> Optional[Action]:
        if self._i >= len(self._actions):
            return None
        action = self._actions[self._i]
        self._i += 1
        return action


def _gate_action(action: Action, defense: Defense, scenario: BenchScenario, env_state) -> Optional[str]:
    """Apply the enforcing controls of a defense to one proposed action; return a
    denial reason or None. (Advisory A1 does not gate; it labels observations.)"""
    controls = defense.controls
    if Control.ALLOWLIST in controls:
        tool = _ACTION_TOOL.get(action.type)
        if tool is not None and tool not in scenario.allowed_tools():
            return f"ToolNotAllowed: '{tool}'"
    if Control.EGRESS_GATE in controls:
        token = env_state.canary_in(action.payload)
        if token is not None:
            return f"EgressBlocked: canary {token!r}"
    if Control.TASK_SCOPE in controls:
        decision = evaluate(action, scenario.policy, env_state)
        if decision.denied:
            return decision.reason
    return None


def run_case_adapter(
    scenario: BenchScenario,
    defense: Defense,
    adapter: AgentAdapter,
    attack: Attack = DEFAULT_ATTACK,
    *,
    max_steps: int = 64,
) -> CaseResult:
    """Run a product (via its adapter) as deployed, interposing our controls."""
    env = materialize_env(scenario, attack)
    executed: list[Action] = []
    denied: list[Action] = []

    adapter.reset(scenario)
    observation: Optional[str] = None
    for _ in range(max_steps):
        action = adapter.propose(observation)
        if action is None:
            break
        reason = _gate_action(action, defense, scenario, hpc_env_adapter(env))
        if reason is not None:
            denied.append(action)
            observation = f"DENIED: {reason}"
            continue
        observation = apply_action(env, action)
        executed.append(action)

    oracle = security_oracle(executed, scenario.policy, scenario.consequence, hpc_env_adapter(env))
    return CaseResult(
        scenario_id=scenario.id,
        defense=defense,
        attack_id=attack.id,
        consequence=scenario.consequence,
        security=oracle.verdict,
        utility_preserved=scenario.utility(env),
        executed=tuple(executed),
        denied=tuple(denied),
    )
