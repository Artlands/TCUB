"""Cluster adapters: the stub records effects; the Slurm adapter's real
filesystem ops work in a sandbox and its kill-switch fires on escape."""

import tempfile
import unittest

from taskbound_core import Action, ActionType
from taskbound_harness import SlurmClusterAdapter, StubCluster
from taskbound_harness.cluster import SandboxViolation
from taskbound_harness.scenario import ClusterSeed


class TestStubCluster(unittest.TestCase):
    def test_read_returns_seeded_content(self):
        c = StubCluster(ClusterSeed(files={"/a/b": "hello"}))
        obs = c.execute(Action(ActionType.READ, path="/a/b"))
        self.assertTrue(obs.ok)
        self.assertEqual(obs.content, "hello")

    def test_write_and_submit_and_egress_recorded(self):
        c = StubCluster(ClusterSeed())
        c.execute(Action(ActionType.WRITE, path="/scratch/x", payload="data"))
        c.execute(Action(ActionType.SUBMIT_JOB, nodes=3))
        c.execute(Action(ActionType.EGRESS, sink="s", payload="p"))
        self.assertEqual(c.files["/scratch/x"], "data")
        self.assertEqual(c.writes, ["/scratch/x"])
        self.assertEqual(c.jobs[0]["nodes"], 3)
        self.assertEqual(c.egress_log, [("s", "p")])


class TestSlurmAdapterFilesystem(unittest.TestCase):
    def test_write_then_read_roundtrip_in_sandbox(self):
        with tempfile.TemporaryDirectory() as root:
            c = SlurmClusterAdapter(root)
            c.execute(Action(ActionType.WRITE, path="/scratch/job/out.txt", payload="hi"))
            obs = c.execute(Action(ActionType.READ, path="/scratch/job/out.txt"))
            self.assertTrue(obs.ok)
            self.assertEqual(obs.content, "hi")

    def test_kill_switch_blocks_path_escape(self):
        with tempfile.TemporaryDirectory() as root:
            c = SlurmClusterAdapter(root)
            with self.assertRaises(SandboxViolation):
                c.execute(Action(ActionType.WRITE, path="/../../etc/evil", payload="x"))


if __name__ == "__main__":
    unittest.main()
