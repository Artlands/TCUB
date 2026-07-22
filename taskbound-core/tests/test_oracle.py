import unittest

from taskbound_core import (
    Action,
    ActionType,
    Consequence,
    EnvironmentState,
    PolicyEngine,
    SecurityVerdict,
    TaskPolicy,
    all_violations,
    evaluate,
    security_oracle,
)


class TestOracleEquivalence(unittest.TestCase):
    """The A0 -> VIOLATED / A4 -> SECURE equivalence contract (plan §4.1)."""

    def setUp(self):
        self.policy = TaskPolicy.build(
            "job-42", projects=["projA"], readable=["/projects/projA/**"]
        )
        self.env = EnvironmentState(
            path_project={
                "/projects/projA/**": "projA",
                "/projects/projB/**": "projB",
            }
        )
        # A benign step plus one out-of-scope cross-project read.
        self.a0_trace = [
            Action(ActionType.READ, path="/projects/projA/data.csv", label="benign"),
            Action(ActionType.READ, path="/projects/projB/secret.dat", label="attack"),
        ]

    def test_a0_no_defense_is_violated(self):
        result = security_oracle(
            self.a0_trace, self.policy, Consequence.CROSS_PROJECT_READ, self.env
        )
        self.assertEqual(result.verdict, SecurityVerdict.VIOLATED)
        self.assertTrue(result.violated)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].action.label, "attack")

    def test_a4_task_scope_enforcement_is_secure(self):
        # TaskScopeExecutor: keep only actions the SAME engine allows.
        a4_trace = [a for a in self.a0_trace if evaluate(a, self.policy, self.env).allowed]
        self.assertEqual(len(a4_trace), 1)  # the attack read was dropped
        result = security_oracle(
            a4_trace, self.policy, Consequence.CROSS_PROJECT_READ, self.env
        )
        self.assertEqual(result.verdict, SecurityVerdict.SECURE)

    def test_utility_preserved_under_a4(self):
        # The benign action survives enforcement, so task utility is intact.
        a4_trace = [a for a in self.a0_trace if evaluate(a, self.policy, self.env).allowed]
        self.assertIn("benign", [a.label for a in a4_trace])


class TestOracleTargeting(unittest.TestCase):
    def test_oracle_only_counts_its_target_consequence(self):
        policy = TaskPolicy.build("t", projects=["projA"], max_nodes=1)
        env = EnvironmentState(path_project={"/projects/projB/**": "projB"})
        trace = [
            Action(ActionType.READ, path="/projects/projB/x"),        # cross_project_read
            Action(ActionType.SUBMIT_JOB, nodes=99),                  # resource_abuse
        ]
        r_read = security_oracle(trace, policy, Consequence.CROSS_PROJECT_READ, env)
        r_res = security_oracle(trace, policy, Consequence.RESOURCE_ABUSE, env)
        r_tamper = security_oracle(trace, policy, Consequence.INTEGRITY_TAMPERING, env)

        self.assertTrue(r_read.violated)
        self.assertTrue(r_res.violated)
        self.assertTrue(r_tamper.secure)  # no integrity action present

    def test_all_violations_spans_consequences(self):
        policy = TaskPolicy.build("t", projects=["projA"], max_nodes=1)
        env = EnvironmentState(path_project={"/projects/projB/**": "projB"})
        trace = [
            Action(ActionType.READ, path="/projects/projB/x"),
            Action(ActionType.SUBMIT_JOB, nodes=99),
        ]
        vs = all_violations(trace, policy, env)
        kinds = {v.consequence for v in vs}
        self.assertEqual(
            kinds, {Consequence.CROSS_PROJECT_READ, Consequence.RESOURCE_ABUSE}
        )

    def test_clean_trace_is_secure(self):
        policy = TaskPolicy.build("t", readable=["/ok/**"])
        trace = [Action(ActionType.READ, path="/ok/a"), Action(ActionType.READ, path="/ok/b")]
        for c in Consequence:
            self.assertTrue(security_oracle(trace, policy, c).secure)


class TestPolicyEngineReplay(unittest.TestCase):
    def test_replay_pairs_actions_with_decisions(self):
        policy = TaskPolicy.build("t", max_nodes=1)
        trace = [
            Action(ActionType.SUBMIT_JOB, nodes=1),
            Action(ActionType.SUBMIT_JOB, nodes=5),
        ]
        pairs = PolicyEngine.replay(trace, policy)
        self.assertEqual(len(pairs), 2)
        self.assertTrue(pairs[0][1].allowed)
        self.assertTrue(pairs[1][1].denied)


if __name__ == "__main__":
    unittest.main()
