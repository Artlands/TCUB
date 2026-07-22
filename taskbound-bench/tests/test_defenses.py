"""The enforcing gates and the advisory provenance labeler."""

import unittest

from agentdojo.functions_runtime import FunctionCall
from agentdojo.types import ChatToolResultMessage, text_content_block_from_string

from taskbound_bench import (
    EgressGateExecutor,
    HPCEnv,
    ProvenanceLabeler,
    ToolAllowlistExecutor,
    hpc_action_mapper,
    hpc_env_adapter,
    scenarios,
)


class TestToolAllowlist(unittest.TestCase):
    def test_blocks_unlisted_tool_allows_listed(self):
        gate = ToolAllowlistExecutor(allowed_tools={"read_file"})
        self.assertIsNotNone(gate._judge(FunctionCall(function="edit_file", args={}, id="a"), None))
        self.assertIsNone(gate._judge(FunctionCall(function="read_file", args={}, id="b"), None))


class TestEgressGate(unittest.TestCase):
    def test_blocks_payload_carrying_canary(self):
        env = HPCEnv(canaries={"CANARY-X": "/projects/projB/secret.dat"})
        gate = EgressGateExecutor(hpc_action_mapper, hpc_env_adapter)
        leaking = FunctionCall(function="write_file", args={"path": "/scratch/x", "content": "leak CANARY-X"}, id="e1")
        clean = FunctionCall(function="write_file", args={"path": "/scratch/x", "content": "clean"}, id="e2")
        self.assertIsNotNone(gate._judge(leaking, env))
        self.assertIsNone(gate._judge(clean, env))


class TestProvenanceLabeler(unittest.TestCase):
    def test_labels_out_of_scope_read_as_untrusted(self):
        scenario = scenarios.get("cross_project_read.summarize_log")
        labeler = ProvenanceLabeler(scenario.policy)
        call = FunctionCall(function="read_file", args={"path": "/projects/projB/secret.dat"}, id="r")
        tool_msg = ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("weights")],
            tool_call_id="r",
            tool_call=call,
            error=None,
        )
        env = scenario.base_env_factory()
        _, _, _, out, _ = labeler.query("", None, env, [tool_msg])
        labeled = out[0]["content"][0]["content"]
        self.assertTrue(labeled.startswith("⟦prov"))
        self.assertIn("UNTRUSTED", labeled)  # projB is outside the task's project scope

    def test_labels_in_scope_read_as_trusted_and_is_idempotent(self):
        scenario = scenarios.get("cross_project_read.summarize_log")
        labeler = ProvenanceLabeler(scenario.policy)
        call = FunctionCall(function="read_file", args={"path": "/projects/projA/inputs/run.log"}, id="r")
        tool_msg = ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("epoch 9")],
            tool_call_id="r",
            tool_call=call,
            error=None,
        )
        env = scenario.base_env_factory()
        _, _, _, once, _ = labeler.query("", None, env, [tool_msg])
        self.assertIn("trusted", once[0]["content"][0]["content"])
        # running again must not double-label
        _, _, _, twice, _ = labeler.query("", None, env, once)
        self.assertEqual(once[0]["content"][0]["content"], twice[0]["content"][0]["content"])


if __name__ == "__main__":
    unittest.main()
