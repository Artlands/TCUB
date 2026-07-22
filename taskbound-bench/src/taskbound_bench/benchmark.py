"""The thin benchmark runner (the ``benchmark.py`` referenced in the plan).

Runs a bench scenario through the real AgentDojo pipeline under a defense and a
chosen attack, extracts the *executed* action trace from the resulting messages,
and scores it with the shared ``taskbound_core`` oracle to produce USR and ASR.

Key point mirroring the harness: a call the A4 ``TaskScopeExecutor`` denies comes
back as a tool result carrying an error, so it is excluded from the executed
trace -- the oracle therefore scores A4 SECURE (ASR 0) and A0 VIOLATED (ASR 1)
by construction, off the same policy engine that did the denying.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from agentdojo.agent_pipeline import BasePipelineElement, ToolsExecutor
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.types import ChatMessage

from taskbound_core import Action, Consequence, SecurityVerdict, security_oracle

from .attacks import DEFAULT_ATTACK, Attack, all_attacks
from .env import HPCEnv
from .executor import TaskScopeExecutor
from .mapping import hpc_action_mapper, hpc_env_adapter
from .pipeline import ScriptedLLM, build_pipeline
from .scenario import BenchScenario
from .scenarios import all_scenarios
from .tools import register_hpc_tools

__all__ = [
    "Defense",
    "CaseResult",
    "MatrixReport",
    "materialize_env",
    "run_case",
    "run_matrix",
    "run_full_matrix",
]


class Defense(Enum):
    A0 = "A0"  # no defense (bare ToolsExecutor)
    A4 = "A4"  # task-scope enforcement (TaskScopeExecutor)


@dataclass(frozen=True)
class CaseResult:
    scenario_id: str
    defense: Defense
    attack_id: str
    consequence: Consequence
    security: SecurityVerdict
    utility_preserved: bool
    executed: tuple[Action, ...] = ()
    denied: tuple[Action, ...] = ()

    @property
    def usr(self) -> float:
        """Utility Success Rate over this single case."""
        return 1.0 if self.utility_preserved else 0.0

    @property
    def asr(self) -> float:
        """Attack Success Rate over this single case."""
        return 1.0 if self.security is SecurityVerdict.VIOLATED else 0.0


def materialize_env(scenario: BenchScenario, attack: Attack) -> HPCEnv:
    """Build the scenario's benign env, then plant the attack-rendered payload
    into the injection site."""
    env = scenario.base_env_factory()
    env.files[scenario.injection_site] = env.files.get(scenario.injection_site, "") + attack.render(
        scenario.injection_instruction
    )
    return env


def _split_executed_denied(
    messages: list[ChatMessage],
) -> tuple[list[Action], list[Action]]:
    """Map requested tool calls to Actions, split by whether they executed.

    A tool result with a non-null ``error`` (a PolicyDenied denial, or any
    execution failure) means its call did not take effect, so it is not part of
    the executed trace.
    """
    errored_ids = {
        m.get("tool_call_id")
        for m in messages
        if m.get("role") == "tool" and m.get("error") is not None
    }
    executed: list[Action] = []
    denied: list[Action] = []
    for message in messages:
        if message.get("role") != "assistant" or not message.get("tool_calls"):
            continue
        for tool_call in message["tool_calls"]:
            action = hpc_action_mapper(tool_call)
            if action is None:
                continue
            (denied if tool_call.id in errored_ids else executed).append(action)
    return executed, denied


def _make_executor(scenario: BenchScenario, defense: Defense) -> BasePipelineElement:
    if defense is Defense.A4:
        return TaskScopeExecutor(scenario.policy, hpc_action_mapper, env_adapter=hpc_env_adapter)
    return ToolsExecutor()


def run_case(
    scenario: BenchScenario,
    defense: Defense,
    attack: Attack = DEFAULT_ATTACK,
    *,
    susceptible: bool = True,
    llm: Optional[BasePipelineElement] = None,
) -> CaseResult:
    """Run one matrix cell (scenario × defense × attack) through the real pipeline."""
    if llm is None:
        script = scenario.susceptible_script() if susceptible else scenario.robust_script()
        llm = ScriptedLLM(script)

    runtime = FunctionsRuntime([])
    register_hpc_tools(runtime)
    env = materialize_env(scenario, attack)

    pipeline = build_pipeline(scenario.system_prompt, llm, _make_executor(scenario, defense))
    _, _, env_out, messages, _ = pipeline.query(scenario.user_prompt, runtime, env)

    env_state = hpc_env_adapter(env_out)
    executed, denied = _split_executed_denied(list(messages))
    oracle = security_oracle(executed, scenario.policy, scenario.consequence, env_state)

    return CaseResult(
        scenario_id=scenario.id,
        defense=defense,
        attack_id=attack.id,
        consequence=scenario.consequence,
        security=oracle.verdict,
        utility_preserved=scenario.utility(env_out),
        executed=tuple(executed),
        denied=tuple(denied),
    )


def run_matrix(scenario: BenchScenario, attack: Attack = DEFAULT_ATTACK) -> dict[Defense, CaseResult]:
    """Run one scenario under A0 and A4 (fresh susceptible model each). Returns
    the joint result -- the USR/ASR pair the paper reports per cell."""
    return {d: run_case(scenario, d, attack) for d in (Defense.A0, Defense.A4)}


@dataclass(frozen=True)
class MatrixReport:
    cells: tuple[CaseResult, ...]

    def _subset(self, defense: Defense) -> list[CaseResult]:
        return [c for c in self.cells if c.defense is defense]

    def usr(self, defense: Defense) -> float:
        cells = self._subset(defense)
        return sum(c.usr for c in cells) / len(cells) if cells else 0.0

    def asr(self, defense: Defense) -> float:
        cells = self._subset(defense)
        return sum(c.asr for c in cells) / len(cells) if cells else 0.0


def run_full_matrix(
    scenarios: Optional[list[BenchScenario]] = None,
    attacks: Optional[list[Attack]] = None,
) -> MatrixReport:
    """The whole deterministic matrix: scenarios × attacks × {A0, A4}."""
    scenarios = scenarios if scenarios is not None else all_scenarios()
    attacks = attacks if attacks is not None else all_attacks()
    cells = [
        run_case(scenario, defense, attack)
        for scenario in scenarios
        for attack in attacks
        for defense in (Defense.A0, Defense.A4)
    ]
    return MatrixReport(cells=tuple(cells))
