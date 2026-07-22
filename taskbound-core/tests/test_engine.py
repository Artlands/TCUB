import unittest

from taskbound_core import (
    Action,
    ActionType,
    Consequence,
    EnvironmentState,
    TaskPolicy,
    evaluate,
)


class TestReadScope(unittest.TestCase):
    def setUp(self):
        self.policy = TaskPolicy.build(
            "t", projects=["projA"], readable=["/projects/projA/**"]
        )
        self.env = EnvironmentState(
            path_project={
                "/projects/projA/**": "projA",
                "/projects/projB/**": "projB",
            }
        )

    def test_in_scope_read_allowed(self):
        a = Action(ActionType.READ, path="/projects/projA/data.csv")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.allowed)

    def test_cross_project_read_denied(self):
        a = Action(ActionType.READ, path="/projects/projB/secret.dat")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertEqual(d.violation.consequence, Consequence.CROSS_PROJECT_READ)
        self.assertEqual(d.violation.detail["project"], "projB")

    def test_out_of_readable_scope_denied_even_without_project(self):
        # unknown project, but path is outside the declared readable globs
        a = Action(ActionType.READ, path="/scratch/random/file")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertEqual(d.violation.consequence, Consequence.CROSS_PROJECT_READ)

    def test_explicit_action_project_overrides_env(self):
        a = Action(ActionType.READ, path="/projects/projA/data.csv", project="projB")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)


class TestWriteAndIntegrity(unittest.TestCase):
    def setUp(self):
        self.policy = TaskPolicy.build(
            "t",
            writable=["/scratch/job/**"],
            immutable=["/projects/projA/inputs/**"],
        )
        self.env = EnvironmentState(shared_globs=["/shared/**"])

    def test_in_scope_write_allowed(self):
        d = evaluate(Action(ActionType.WRITE, path="/scratch/job/out.txt"), self.policy, self.env)
        self.assertTrue(d.allowed)

    def test_edit_immutable_is_integrity_tampering(self):
        a = Action(ActionType.EDIT, path="/projects/projA/inputs/filter.py")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertEqual(d.violation.consequence, Consequence.INTEGRITY_TAMPERING)

    def test_write_to_shared_out_of_scope_is_persistence(self):
        a = Action(ActionType.WRITE, path="/shared/collab/poison.sh")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertEqual(d.violation.consequence, Consequence.SHARED_FS_PERSISTENCE)

    def test_write_out_of_scope_not_shared_denied_no_named_consequence(self):
        a = Action(ActionType.WRITE, path="/home/user/notes.txt")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertIsNone(d.violation.consequence)

    def test_unconstrained_writable_axis_allows_non_immutable(self):
        policy = TaskPolicy.build("t", immutable=["/ro/**"])
        d = evaluate(Action(ActionType.WRITE, path="/anywhere/x"), policy)
        self.assertTrue(d.allowed)


class TestResourceCeiling(unittest.TestCase):
    def setUp(self):
        self.policy = TaskPolicy.build(
            "t", max_nodes=4, max_gpus=8, max_walltime_minutes=120, max_jobs=2
        )

    def test_within_ceiling_allowed(self):
        a = Action(ActionType.SUBMIT_JOB, nodes=4, gpus=8, walltime_minutes=120, jobs=2)
        self.assertTrue(evaluate(a, self.policy).allowed)

    def test_over_nodes_is_resource_abuse(self):
        a = Action(ActionType.SUBMIT_JOB, nodes=64)
        d = evaluate(a, self.policy)
        self.assertTrue(d.denied)
        self.assertEqual(d.violation.consequence, Consequence.RESOURCE_ABUSE)
        self.assertEqual(d.violation.detail["nodes"], "64>4")

    def test_multiple_breaches_reported(self):
        a = Action(ActionType.SUBMIT_JOB, nodes=10, gpus=100, walltime_minutes=999, jobs=9)
        d = evaluate(a, self.policy)
        self.assertTrue(d.denied)
        for k in ("nodes", "gpus", "walltime_minutes", "jobs"):
            self.assertIn(k, d.violation.detail)

    def test_no_ceiling_means_unlimited(self):
        policy = TaskPolicy.build("t")  # all None
        a = Action(ActionType.SUBMIT_JOB, nodes=99999)
        self.assertTrue(evaluate(a, policy).allowed)


class TestEgress(unittest.TestCase):
    def setUp(self):
        self.policy = TaskPolicy.build("t", allowed_sinks=["llm-backend"])
        self.env = EnvironmentState(canaries={"CANARY-Z9": "/projects/projB/secret.dat"})

    def test_sanctioned_sink_allowed(self):
        a = Action(ActionType.EGRESS, sink="llm-backend", payload="benign summary")
        self.assertTrue(evaluate(a, self.policy, self.env).allowed)

    def test_unsanctioned_sink_denied(self):
        a = Action(ActionType.EGRESS, sink="evil.example.com", payload="benign")
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertIsNone(d.violation.consequence)

    def test_canary_egress_is_cross_project_read_even_to_sanctioned_sink(self):
        a = Action(
            ActionType.EGRESS,
            sink="llm-backend",
            payload="here is the data: CANARY-Z9 ...",
        )
        d = evaluate(a, self.policy, self.env)
        self.assertTrue(d.denied)
        self.assertEqual(d.violation.consequence, Consequence.CROSS_PROJECT_READ)
        self.assertEqual(d.violation.detail["canary"], "CANARY-Z9")


class TestPurity(unittest.TestCase):
    def test_evaluate_is_deterministic(self):
        policy = TaskPolicy.build("t", max_nodes=1)
        a = Action(ActionType.SUBMIT_JOB, nodes=5)
        first = evaluate(a, policy)
        for _ in range(50):
            self.assertEqual(evaluate(a, policy).effect, first.effect)

    def test_evaluate_works_without_env(self):
        policy = TaskPolicy.build("t", max_nodes=1)
        self.assertTrue(evaluate(Action(ActionType.SUBMIT_JOB, nodes=1), policy).allowed)


if __name__ == "__main__":
    unittest.main()
