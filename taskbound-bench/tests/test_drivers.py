"""The two evaluation axes: reference-model sweep and the agent-product adapter."""

import unittest

from taskbound_core import ActionType, SecurityVerdict
from taskbound_bench import (
    Defense,
    FakeAgentAdapter,
    ScriptedLLM,
    reference_axis_sweep,
    run_case_adapter,
    scenarios,
)

_SECURE = SecurityVerdict.SECURE
_VIOLATED = SecurityVerdict.VIOLATED


class TestReferenceAxis(unittest.TestCase):
    def test_sweep_over_three_models(self):
        # Fixed scaffold, swappable model. Real usage passes model LLM elements;
        # here three deterministic stand-ins stand for three models.
        factories = {
            f"model-{k}": (lambda s: ScriptedLLM(s.susceptible_script()))
            for k in ("a", "b", "c")
        }
        reports = reference_axis_sweep(factories, defenses=[Defense.A0, Defense.A4])
        self.assertEqual(set(reports), {"model-a", "model-b", "model-c"})
        for report in reports.values():
            self.assertEqual(report.asr(Defense.A0), 1.0)
            self.assertEqual(report.asr(Defense.A4), 0.0)
            self.assertEqual(report.usr(Defense.A4), 1.0)


class TestAgentProductAxis(unittest.TestCase):
    def test_adapter_a0_violated_a4_secure_with_utility(self):
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                adapter = FakeAgentAdapter.from_scenario(scenario)
                a0 = run_case_adapter(scenario, Defense.A0, adapter)
                a4 = run_case_adapter(scenario, Defense.A4, adapter)
                self.assertIs(a0.security, _VIOLATED)
                self.assertIs(a4.security, _SECURE)
                self.assertTrue(a4.utility_preserved)
                self.assertEqual(len(a4.denied), 1)  # exactly the malicious action

    def test_task_scope_wraps_a_products_action_stream(self):
        # A4 interposed on the product's actions blocks the out-of-scope one.
        scenario = scenarios.get("cross_project_read.summarize_log")
        adapter = FakeAgentAdapter.from_scenario(scenario)
        result = run_case_adapter(scenario, Defense.A4, adapter)
        self.assertFalse(any(a.path == "/projects/projB/secret.dat" for a in result.executed))
        self.assertTrue(any(a.path == "/projects/projB/secret.dat" for a in result.denied))

    def test_robust_product_is_secure_under_a0(self):
        scenario = scenarios.get("resource_abuse.train_config")
        adapter = FakeAgentAdapter.from_scenario(scenario, susceptible=False)
        result = run_case_adapter(scenario, Defense.A0, adapter)
        self.assertIs(result.security, _SECURE)
        self.assertTrue(result.utility_preserved)

    def test_allowlist_on_adapter_blocks_integrity(self):
        scenario = scenarios.get("integrity_tampering.threshold_edit")
        adapter = FakeAgentAdapter.from_scenario(scenario)
        result = run_case_adapter(scenario, Defense.A2, adapter)
        self.assertIs(result.security, _SECURE)  # edit_file not on the task allowlist


if __name__ == "__main__":
    unittest.main()
