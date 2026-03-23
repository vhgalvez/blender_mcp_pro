import unittest

from blender_mcp_pro.protocol import NDJSONProtocol, ProtocolError


class NDJSONProtocolTests(unittest.TestCase):
    def test_parse_auth_message(self) -> None:
        protocol = NDJSONProtocol()

        messages = protocol.feed_data(b'{"id":"auth-1","type":"auth","token":"secret"}\n')

        self.assertEqual(
            messages,
            [
                {
                    "id": "auth-1",
                    "type": "auth",
                    "token": "secret",
                    "kind": "auth",
                }
            ],
        )

    def test_parse_legacy_command_message(self) -> None:
        protocol = NDJSONProtocol()

        messages = protocol.feed_data(
            b'{"id":"cmd-1","type":"command","command":"get_scene_info","params":{}}\n'
        )

        self.assertEqual(messages[0]["kind"], "legacy_command")
        self.assertEqual(messages[0]["command"], "get_scene_info")
        self.assertEqual(messages[0]["params"], {})

    def test_parse_jsonrpc_message(self) -> None:
        protocol = NDJSONProtocol()

        messages = protocol.feed_data(
            b'{"jsonrpc":"2.0","id":"req-1","method":"tools/list","params":{}}\n'
        )

        self.assertEqual(
            messages,
            [
                {
                    "id": "req-1",
                    "kind": "jsonrpc",
                    "method": "tools/list",
                    "params": {},
                }
            ],
        )

    def test_rejects_non_object_params(self) -> None:
        protocol = NDJSONProtocol()

        with self.assertRaises(ProtocolError) as context:
            protocol.feed_data(
                b'{"jsonrpc":"2.0","id":"req-1","method":"tools/call","params":[]}\n'
            )

        self.assertEqual(context.exception.code, "invalid_params")

    def test_rejects_empty_string_id(self) -> None:
        protocol = NDJSONProtocol()

        with self.assertRaises(ProtocolError) as context:
            protocol.feed_data(b'{"id":"   ","type":"auth","token":"secret"}\n')

        self.assertEqual(context.exception.code, "missing_request_id")

    def test_rejects_invalid_json(self) -> None:
        protocol = NDJSONProtocol()

        with self.assertRaises(ProtocolError) as context:
            protocol.feed_data(b'{"id":"x","type":"auth",}\n')

        self.assertEqual(context.exception.code, "invalid_json")


if __name__ == "__main__":
    unittest.main()
