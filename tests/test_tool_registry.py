import unittest

from blender_mcp_pro.tool_registry import (
    COMMAND_SCHEMAS,
    build_input_schema,
    get_backend_tool,
    iter_backend_tools,
)
from client.tools_registry import TOOLS, TOOLS_BY_NAME


class BackendToolRegistryTests(unittest.TestCase):
    def test_backend_specs_have_consistent_required_fields(self) -> None:
        for spec in iter_backend_tools():
            self.assertTrue(
                set(spec["required"]).issubset(spec["params"]),
                msg=f"Required fields must be present in params for {spec['command']}",
            )

    def test_backend_commands_have_schemas(self) -> None:
        for spec in iter_backend_tools():
            schema = build_input_schema(spec)
            self.assertEqual(schema["type"], "object")
            self.assertIn(spec["command"], COMMAND_SCHEMAS)

    def test_backend_tool_lookup_supports_command_and_public_name(self) -> None:
        scene_info = get_backend_tool("get_scene_info")
        scene_info_alias = get_backend_tool("scene_info")

        self.assertIsNotNone(scene_info)
        self.assertIsNotNone(scene_info_alias)
        self.assertEqual(scene_info["command"], scene_info_alias["command"])


class ClientToolRegistryTests(unittest.TestCase):
    def test_client_tool_names_are_unique(self) -> None:
        self.assertEqual(len(TOOLS), len(TOOLS_BY_NAME))

    def test_all_tools_have_input_schema(self) -> None:
        for tool in TOOLS:
            self.assertIn("input_schema", tool)
            self.assertEqual(tool["input_schema"]["type"], "object")

    def test_server_tools_have_backend_command(self) -> None:
        for tool in TOOLS:
            if tool["availability"] == "server":
                self.assertIsInstance(tool["backend_command"], str)
                self.assertTrue(tool["backend_command"])


if __name__ == "__main__":
    unittest.main()
