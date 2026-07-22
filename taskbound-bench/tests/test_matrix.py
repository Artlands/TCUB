"""M4 exit criterion: the full deterministic matrix (4 consequences × multiple
user/injection tasks × attack registry × {A0, A4}) runs and is deterministic."""

import unittest

from taskbound_core import Consequence, SecurityVerdict
from taskbound_bench import (
    Defense,
    attacks,
    run_case,
    run_full_matrix,
    scenarios,
)


class TestRegistry(unittest.TestCase):
    def test_all_four_consequences_have_multiple_tasks(self):
        for consequence in Consequence:
            tasks = scenarios.by_consequence(consequence)
            self.assertGreaterEqual(len(tasks), 2, msg=f"{consequence} needs >=2 user tasks")
        self.assertEqual(len(scenarios.all_scenarios()), 8)

    def test_attack_registry_nonempty_and_distinct(self):
        rendered = {a.render("do X") for a in attacks.all_attacks()}
        self.assertGreaterEqual(len(attacks.all_attacks()), 3)
        # every attack renders a distinct payload
        self.assertEqual(len(rendered), len(attacks.all_attacks()))


class TestFullMatrix(unittest.TestCase):
    def test_every_cell_a0_violated_a4_secure_utility_preserved(self):
        report = run_full_matrix()
        # 8 scenarios × 4 attacks × 2 defenses
        self.assertEqual(len(report.cells), 8 * 4 * 2)
        for cell in report.cells:
            with self.subTest(cell=f"{cell.scenario_id}/{cell.attack_id}/{cell.defense.value}"):
                if cell.defense is Defense.A0:
                    self.assertIs(cell.security, SecurityVerdict.VIOLATED)
                else:
                    self.assertIs(cell.security, SecurityVerdict.SECURE)
                self.assertTrue(cell.utility_preserved)  # utility preserved everywhere

    def test_aggregate_usr_asr(self):
        report = run_full_matrix()
        self.assertEqual(report.asr(Defense.A0), 1.0)
        self.assertEqual(report.asr(Defense.A4), 0.0)
        self.assertEqual(report.usr(Defense.A0), 1.0)
        self.assertEqual(report.usr(Defense.A4), 1.0)

    def test_deterministic_across_repeats(self):
        a = run_full_matrix()
        b = run_full_matrix()
        key = lambda r: [
            (c.scenario_id, c.attack_id, c.defense.value, c.security.value, c.utility_preserved)
            for c in r.cells
        ]
        self.assertEqual(key(a), key(b))


class TestAttackInvarianceAndControl(unittest.TestCase):
    def test_verdict_invariant_across_attacks(self):
        scenario = scenarios.get("integrity_tampering.threshold_edit")
        for attack in attacks.all_attacks():
            with self.subTest(attack=attack.id):
                a0 = run_case(scenario, Defense.A0, attack)
                a4 = run_case(scenario, Defense.A4, attack)
                self.assertIs(a0.security, SecurityVerdict.VIOLATED)
                self.assertIs(a4.security, SecurityVerdict.SECURE)

    def test_robust_agent_is_secure_under_a0(self):
        # A non-susceptible agent (ignores the injection) scores SECURE even with
        # no defense -- the oracle is not trivially always-VIOLATED.
        for scenario in scenarios.all_scenarios():
            with self.subTest(scenario=scenario.id):
                result = run_case(scenario, Defense.A0, susceptible=False)
                self.assertIs(result.security, SecurityVerdict.SECURE)
                self.assertTrue(result.utility_preserved)


if __name__ == "__main__":
    unittest.main()
