"""M2 exit criterion: every scenario runs A0 -> VIOLATED and A4 -> SECURE with
utility preserved, end-to-end on the stub cluster."""

import unittest

from taskbound_core import SecurityVerdict
from taskbound_harness import Defense, run_scenario, scenarios, verify_scenario
from taskbound_harness.driver import ScriptedDriver, robust_trace


class TestEquivalenceContract(unittest.TestCase):
    def test_all_four_consequences_registered(self):
        ids = set(scenarios.REGISTRY)
        self.assertEqual(len(ids), 4)
        consequences = {s.consequence for s in scenarios.all_scenarios()}
        self.assertEqual(len(consequences), 4)  # one distinct consequence each

    def test_each_scenario_meets_expected_contract(self):
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                outcome = verify_scenario(scenario)
                self.assertTrue(
                    outcome["ok"],
                    msg=(
                        f"{scenario.id}: A0={outcome['a0'].security} "
                        f"A4={outcome['a4'].security} "
                        f"util_a4={outcome['a4'].utility_preserved}"
                    ),
                )

    def test_a0_violated_a4_secure_explicit(self):
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                a0 = run_scenario(scenario, Defense.A0)
                a4 = run_scenario(scenario, Defense.A4)
                self.assertIs(a0.security, SecurityVerdict.VIOLATED)
                self.assertIs(a4.security, SecurityVerdict.SECURE)
                self.assertTrue(a4.utility_preserved)

    def test_a4_blocks_exactly_the_malicious_action(self):
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                a4 = run_scenario(scenario, Defense.A4)
                self.assertEqual(len(a4.denied), 1)
                denied_action, _reason = a4.denied[0]
                self.assertEqual(denied_action, scenario.malicious_action)
                self.assertNotIn(scenario.malicious_action, a4.executed)
                for benign in scenario.benign_actions:
                    self.assertIn(benign, a4.executed)


class TestOracleIsNotTrivial(unittest.TestCase):
    """A robust agent (ignores injection) must score SECURE even under A0 --
    proving the oracle isn't just always-VIOLATED."""

    def test_robust_agent_is_secure_under_a0(self):
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                driver = ScriptedDriver(robust_trace(scenario))
                result = run_scenario(scenario, Defense.A0, driver=driver)
                self.assertIs(result.security, SecurityVerdict.SECURE)
                self.assertTrue(result.utility_preserved)


if __name__ == "__main__":
    unittest.main()
