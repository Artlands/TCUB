"""The metric layer: standard + HPC consequence/severity metrics."""

import unittest

from taskbound_core import SecurityVerdict
from taskbound_bench import (
    Defense,
    benign_usr_baseline,
    compute_metrics,
    default_severity_weights,
    format_joint_table,
    run_full_matrix,
    severity_weighted_risk,
)


class TestMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = list(run_full_matrix().cells)  # default attack, all defenses
        cls.benign = benign_usr_baseline(list(Defense))
        cls.metrics = compute_metrics(cls.cells, cls.benign)

    def test_no_defense_high_asr_no_stcr(self):
        m = self.metrics[Defense.A0]
        self.assertEqual(m.asr, 1.0)
        self.assertEqual(m.usr, 1.0)
        self.assertEqual(m.stcr, 0.0)          # attack never blocked
        self.assertEqual(m.defense_cost, 0.0)

    def test_task_scope_zero_asr_full_stcr_no_utility_cost(self):
        m = self.metrics[Defense.A4]
        self.assertEqual(m.asr, 0.0)
        self.assertEqual(m.stcr, 1.0)          # benign ok AND attack blocked, everywhere
        self.assertEqual(m.usr, 1.0)
        self.assertEqual(m.defense_cost, 0.0)  # enforcement preserves utility
        self.assertEqual((m.uar, m.itr, m.spr), (0.0, 0.0, 0.0))

    def test_consequence_layer_under_no_defense(self):
        m = self.metrics[Defense.A0]
        self.assertEqual((m.uar, m.itr, m.spr), (1.0, 1.0, 1.0))
        # SDER is a magnitude: mean over-ceiling ratio (512/4=128, 256/4=64) -> 96.
        self.assertEqual(m.sder, 96.0)

    def test_allowlist_partial_on_integrity(self):
        m = self.metrics[Defense.A2]
        self.assertEqual(m.itr, 0.0)   # edit_file blocked
        self.assertEqual(m.uar, 1.0)   # authorized-tool abuse not blocked
        self.assertEqual(m.asr, 0.75)  # 6 of 8 scenarios still violated

    def test_severity_weighted_risk_drops_to_zero_under_a4(self):
        a0 = [c for c in self.cells if c.defense is Defense.A0]
        a4 = [c for c in self.cells if c.defense is Defense.A4]
        weights = default_severity_weights()
        self.assertGreater(severity_weighted_risk(a0, weights), 0.0)
        self.assertEqual(severity_weighted_risk(a4, weights), 0.0)

    def test_format_joint_table(self):
        table = format_joint_table(self.metrics)
        self.assertIn("defense", table)
        self.assertIn("A1+A4", table)  # combo row present
        self.assertIn("SDER", table)


if __name__ == "__main__":
    unittest.main()
