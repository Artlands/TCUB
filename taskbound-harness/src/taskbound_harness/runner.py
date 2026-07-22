"""The run loop: drive an agent, apply the defense gate, score with the oracle.

The A4 gate is literally ``taskbound_core.evaluate`` -- the *same* function the
bench's ``TaskScopeExecutor`` uses and the *same* function ``security_oracle``
replays with. So a denied action never executes, never enters the executed
trace, and the oracle therefore scores A4 as SECURE by construction; under A0 the
action executes, enters the trace, and the oracle scores VIOLATED. That identity
is what makes in-memory and real-cluster verdicts equivalent.
"""

from __future__ import annotations

from typing import Optional

from taskbound_core import evaluate, security_oracle

from .cluster import ClusterAdapter, StubCluster
from .driver import Driver, ScriptedDriver, susceptible_trace
from .scenario import Scenario, env_from_seed
from .types import Defense, Observation, ScenarioResult

__all__ = ["run_scenario", "verify_scenario"]


def _utility_preserved(scenario: Scenario, executed: list) -> bool:
    """The benign task still succeeds iff all its required actions executed."""
    return all(action in executed for action in scenario.benign_actions)


def run_scenario(
    scenario: Scenario,
    defense: Defense,
    *,
    driver: Optional[Driver] = None,
    cluster: Optional[ClusterAdapter] = None,
    max_steps: int = 64,
) -> ScenarioResult:
    """Run one scenario under one defense and score it deterministically.

    Defaults model a *susceptible* agent on the in-memory stub cluster, which is
    exactly the M2 end-to-end path.
    """
    if driver is None:
        driver = ScriptedDriver(susceptible_trace(scenario))
    if cluster is None:
        cluster = StubCluster(scenario.seed)

    policy = scenario.policy
    env = env_from_seed(scenario.seed)

    executed: list = []
    denied: list[tuple] = []

    driver.reset(scenario)
    observation: Optional[Observation] = None
    for _ in range(max_steps):
        action = driver.next_action(observation)
        if action is None:
            break
        if defense is Defense.A4:
            decision = evaluate(action, policy, env)
            if decision.denied:
                denied.append((action, decision.reason))
                observation = Observation(False, error=decision.reason)
                continue
        observation = cluster.execute(action)
        executed.append(action)

    oracle = security_oracle(executed, policy, scenario.consequence, env)
    return ScenarioResult(
        scenario_id=scenario.id,
        defense=defense,
        consequence=scenario.consequence,
        security=oracle.verdict,
        utility_preserved=_utility_preserved(scenario, executed),
        executed=tuple(executed),
        denied=tuple(denied),
        violations=oracle.violations,
    )


def verify_scenario(scenario: Scenario) -> dict:
    """Run A0 and A4 for a susceptible agent and check the equivalence contract.

    Returns the two results plus whether they match `scenario.expected`. This is
    the assertion the real-cluster harness must also satisfy (V_mem == V_real).
    """
    a0 = run_scenario(scenario, Defense.A0)
    a4 = run_scenario(scenario, Defense.A4)
    ok = (
        a0.security is scenario.expected.a0
        and a4.security is scenario.expected.a4
        and a4.utility_preserved is scenario.expected.utility_a4
    )
    return {"a0": a0, "a4": a4, "ok": ok}
