"""The NPU meter and the Loaded panel must never silently contradict.

A reviewer filmed TiinyBench showing "My Tiiny 99 / 100" with one 52-unit model
in the Loaded panel, and a 47-unit load refused for want of room. 52 + 47 = 99:
the device's npu/status was still charging 47 units to a model that had rolled
back and left the running list. The two device endpoints disagreed and the page
showed both numbers with no account of the gap.

The fix is honesty: /api/instances names the held units (npu_held) so the rail
can explain why a load is refused though the panel shows room. These tests fail
before that reconciliation existed.

    /usr/bin/python3 -m unittest tests.test_npu_held -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from test_chat import ServerCase  # noqa: E402

LOADED = "deepreinforce-ai/Ornith-1.0-35B"        # 50 units
GHOST = "Qwen/Qwen3-Coder-30B-A3B-Instruct-Turbo"  # 45 units, held after rollback


class TestHeldUnitsAreNamed(ServerCase):
    loaded = [LOADED]

    def device(self):
        status, payload = self.request("/api/instances")
        self.assertEqual(status, 200)
        return payload, payload["devices"][0]

    def test_a_ghost_allocation_is_reported_as_held_not_hidden(self):
        # The device charges 45 units to a model no longer in the running list.
        self.fake.state.ghost = {GHOST: 45}
        payload, dev = self.device()
        # The device's own budget: one running model (50) plus the ghost (45).
        self.assertEqual(dev["npu_used"], 95)
        self.assertEqual(dev["npu_total"], 100)
        # What the Loaded panel can actually account for.
        self.assertEqual(dev["npu_listed"], 50)
        self.assertEqual(len(payload["instances"]), 1)
        # The gap, named rather than left as two contradicting numbers.
        self.assertEqual(dev["npu_held"], 45)

    def test_no_ghost_means_no_held_units(self):
        # The fix must not cry wolf when the two sources agree.
        payload, dev = self.device()
        self.assertEqual(dev["npu_held"], 0)
        self.assertEqual(dev["npu_listed"], dev["npu_used"])


if __name__ == "__main__":
    unittest.main()
