import unittest
from unittest.mock import patch
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENT_DIR = REPO_ROOT / "client"
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))

from mcp_adapter import BlenderMCPAdapter


class FakeClient:
    def __init__(self):
        self.calls = []
        self._prop_counter = 0

    def call(self, command, params=None):
        params = dict(params or {})
        self.calls.append((command, params))

        if command == "create_prop_blockout":
            self._prop_counter += 1
            prop_type = params["prop_type"]
            return {
                "success": True,
                "prop_type": prop_type,
                "root": f"PROP_Root_{prop_type.title()}_{self._prop_counter:03d}",
            }

        return {"success": True, "command": command, "params": params}


class MCPAdapterScenePlanningTests(unittest.TestCase):
    def setUp(self):
        client_patcher = patch("mcp_adapter.BlenderTcpClient.from_env", return_value=FakeClient())
        self.addCleanup(client_patcher.stop)
        self.mock_from_env = client_patcher.start()
        self.adapter = BlenderMCPAdapter()
        self.fake_client = self.adapter.client

    def test_generate_scene_plan_expands_quantity_for_chairs(self):
        result = self.adapter._generate_scene_plan({"description": "crea una mesa con 4 sillas"})

        self.assertTrue(result["success"])
        props = result["plan"]["props"]
        chair_props = [prop for prop in props if prop["prop_type"] == "chair"]
        table_props = [prop for prop in props if prop["prop_type"] == "table"]

        self.assertEqual(len(chair_props), 4)
        self.assertEqual(len(table_props), 1)

    def test_apply_scene_plan_places_each_generated_chair(self):
        result = self.adapter.call_tool("build_scene_from_description", {"description": "crea una mesa con 4 sillas"})

        self.assertEqual(result["workflow"], "apply_scene_plan")
        create_calls = [call for call in self.fake_client.calls if call[0] == "create_prop_blockout"]
        move_calls = [call for call in self.fake_client.calls if call[0] == "move_object"]
        rotate_calls = [call for call in self.fake_client.calls if call[0] == "rotate_object"]

        self.assertEqual(len(create_calls), 5)
        self.assertEqual(len(move_calls), 5)
        self.assertEqual(len(rotate_calls), 5)


if __name__ == "__main__":
    unittest.main()
