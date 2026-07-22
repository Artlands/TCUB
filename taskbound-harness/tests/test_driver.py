"""Drivers emit a normalized Action stream. The scripted driver is deterministic;
the OpenAI reference driver's mapping + turn threading are tested with a fake
transport (no network)."""

import unittest

from taskbound_core import Action, ActionType
from taskbound_harness import OpenAIChatDriver, ScriptedDriver, scenarios
from taskbound_harness.driver import susceptible_trace


class TestScriptedDriver(unittest.TestCase):
    def test_replays_then_stops(self):
        scenario = scenarios.get("resource_abuse.config_comment")
        driver = ScriptedDriver(susceptible_trace(scenario))
        driver.reset(scenario)
        emitted = []
        while (a := driver.next_action(None)) is not None:
            emitted.append(a)
        self.assertEqual(emitted, list(susceptible_trace(scenario)))

    def test_reset_rewinds(self):
        driver = ScriptedDriver([Action(ActionType.READ, path="/x")])
        driver.reset(None)
        self.assertIsNotNone(driver.next_action(None))
        self.assertIsNone(driver.next_action(None))
        driver.reset(None)
        self.assertIsNotNone(driver.next_action(None))


class TestOpenAIChatDriver(unittest.TestCase):
    def _mapper(self, name, args):
        if name == "read_file":
            return Action(ActionType.READ, path=args["path"])
        if name == "submit_job":
            return Action(ActionType.SUBMIT_JOB, nodes=int(args["nodes"]))
        return None

    def test_maps_tool_calls_and_threads_observations(self):
        # Fake transport: first turn a read, second turn a submit, then stop.
        scripted = [
            {"choices": [{"message": {"role": "assistant", "tool_calls": [
                {"id": "t1", "function": {"name": "read_file", "arguments": '{"path": "/projects/projA/x"}'}}
            ]}}]},
            {"choices": [{"message": {"role": "assistant", "tool_calls": [
                {"id": "t2", "function": {"name": "submit_job", "arguments": '{"nodes": 2}'}}
            ]}}]},
            {"choices": [{"message": {"role": "assistant", "content": "done", "tool_calls": []}}]},
        ]
        turns = iter(scripted)
        seen_messages = []

        def transport(messages, tools):
            seen_messages.append(list(messages))
            return next(turns)

        scenario = scenarios.get("cross_project_read.log_note")
        driver = OpenAIChatDriver("m", tools=[], mapper=self._mapper, transport=transport)
        driver.reset(scenario)

        from taskbound_harness import Observation

        a1 = driver.next_action(None)
        a2 = driver.next_action(Observation(True, content="file body"))
        a3 = driver.next_action(Observation(True, content="job-1"))

        self.assertEqual(a1, Action(ActionType.READ, path="/projects/projA/x"))
        self.assertEqual(a2, Action(ActionType.SUBMIT_JOB, nodes=2))
        self.assertIsNone(a3)
        # The observation for t1 was threaded back before the second model turn.
        tool_msgs = [m for m in driver.messages if m.get("role") == "tool"]
        self.assertTrue(any(m.get("tool_call_id") == "t1" for m in tool_msgs))


if __name__ == "__main__":
    unittest.main()
