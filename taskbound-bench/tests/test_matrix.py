"""The deterministic matrix over the full defense set (M4 registry + M5 defenses)."""

import unittest

from taskbound_core import Consequence, SecurityVerdict
from taskbound_bench import (
    Defense,
    attacks,
    run_case,
    run_full_matrix,
    scenarios,
)

_SECURE = SecurityVerdict.SECURE
_VIOLATED = SecurityVerdict.VIOLATED
_A4_DEFENSES = {Defense.A4, Defense.A1_A4, Defense.A2_A4}


class TestRegistry(unittest.TestCase):
    def test_all_four_consequences_have_multiple_tasks(self):
        for consequence in Consequence:
            self.assertGreaterEqual(len(scenarios.by_consequence(consequence)), 2)
        self.assertEqual(len(scenarios.all_scenarios()), 8)

    def test_attack_registry_distinct(self):
        rendered = {a.render("do X") for a in attacks.all_attacks()}
        self.assertGreaterEqual(len(attacks.all_attacks()), 3)
        self.assertEqual(len(rendered), len(attacks.all_attacks()))


class TestDefenseMatrix(unittest.TestCase):
    def test_matrix_shape(self):
        report = run_full_matrix()  # 8 scenarios × 1 default attack × 7 defenses
        self.assertEqual(len(report.cells), 8 * len(Defense))

    def test_any_a4_defense_secures_everything_with_utility(self):
        report = run_full_matrix()
        for cell in report.cells:
            if cell.defense in _A4_DEFENSES:
                with self.subTest(cell=f"{cell.scenario_id}/{cell.defense.label}"):
                    self.assertIs(cell.security, _SECURE)
                    self.assertTrue(cell.utility_preserved)

    def test_no_defense_is_violated_everywhere(self):
        report = run_full_matrix()
        for cell in report.cells:
            if cell.defense is Defense.A0:
                with self.subTest(cell=cell.scenario_id):
                    self.assertIs(cell.security, _VIOLATED)
                    self.assertTrue(cell.utility_preserved)


class TestCheaperDefenses(unittest.TestCase):
    def test_provenance_does_not_reduce_asr(self):
        # A1 is advisory; a susceptible agent ignores labels -> still VIOLATED.
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                self.assertIs(run_case(scenario, Defense.A1).security, _VIOLATED)

    def test_allowlist_blocks_integrity_but_not_authorized_tool_abuse(self):
        # A2 blocks integrity_tampering (edit_file is not a task tool), but not
        # attacks that reuse an authorized tool (read/submit/write).
        for scenario in scenarios.by_consequence(Consequence.INTEGRITY_TAMPERING):
            self.assertIs(run_case(scenario, Defense.A2).security, _SECURE)
        for consequence in (
            Consequence.CROSS_PROJECT_READ,
            Consequence.RESOURCE_ABUSE,
            Consequence.SHARED_FS_PERSISTENCE,
        ):
            for scenario in scenarios.by_consequence(consequence):
                self.assertIs(run_case(scenario, Defense.A2).security, _VIOLATED)


class TestDeterminismAndAttacks(unittest.TestCase):
    def test_deterministic_across_repeats(self):
        key = lambda r: [
            (c.scenario_id, c.defense.name, c.security.value, c.utility_preserved)
            for c in r.cells
        ]
        self.assertEqual(key(run_full_matrix()), key(run_full_matrix()))

    def test_verdict_invariant_across_attacks(self):
        scenario = scenarios.get("integrity_tampering.threshold_edit")
        for attack in attacks.all_attacks():
            with self.subTest(attack=attack.id):
                self.assertIs(run_case(scenario, Defense.A0, attack).security, _VIOLATED)
                self.assertIs(run_case(scenario, Defense.A4, attack).security, _SECURE)

    def test_robust_agent_is_secure_under_a0(self):
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                result = run_case(scenario, Defense.A0, susceptible=False)
                self.assertIs(result.security, _SECURE)
                self.assertTrue(result.utility_preserved)


if __name__ == "__main__":
    unittest.main()
