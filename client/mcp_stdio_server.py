import json
import logging
import os
import sys
from typing import Any

from blender_client import BlenderClientError
from mcp_adapter import BlenderMCPAdapter
from tools_registry import CALLABLE_TOOLS, TOOLS_BY_NAME


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "blender-mcp-pro"
SERVER_VERSION = "1.0.0"


def configure_logging() -> logging.Logger:
    level_name = os.environ.get("BLENDER_MCP_STDIO_LOG", os.environ.get("BLENDER_MCP_ADAPTER_LOG", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("blender_mcp_stdio_server")


LOGGER = configure_logging()


class MCPStdioServer:
    def __init__(self):
        self.adapter = BlenderMCPAdapter()

    def run(self):
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("MCP message must be a JSON object")
            except Exception as exc:
                LOGGER.error("invalid_json %s", exc)
                self._write_error(None, -32700, f"Parse error: {exc}")
                continue

            LOGGER.debug("request %s", json.dumps(message, ensure_ascii=False))
            self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]):
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params", {}) or {}

        if message.get("jsonrpc") != "2.0":
            self._write_error(request_id, -32600, "Invalid Request: jsonrpc must be '2.0'")
            return

        try:
            if method == "initialize":
                self._write_result(
                    request_id,
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": {
                            "name": SERVER_NAME,
                            "version": SERVER_VERSION,
                        },
                    },
                )
                return

            if method == "notifications/initialized":
                return

            if method == "ping":
                self._write_result(request_id, {})
                return

            if method == "tools/list":
                self._write_result(
                    request_id,
                    {
                        "tools": [self._mcp_tool_definition(tool) for tool in CALLABLE_TOOLS],
                    },
                )
                return

            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {}) or {}
                self._write_result(request_id, self._call_tool(tool_name, arguments))
                return

            self._write_error(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:
            LOGGER.exception("request_failed")
            self._write_error(request_id, -32000, str(exc))

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not tool_name:
            return self._tool_error("missing_tool_name", "Tool name is required.")

        tool_meta = TOOLS_BY_NAME.get(tool_name)
        if not tool_meta:
            return self._tool_error("unknown_tool", f"Unknown tool: {tool_name}")

        if tool_meta["availability"] != "server":
            return self._tool_error(
                "tool_not_implemented",
                tool_meta["description"],
                {
                    "tool": tool_name,
                    "availability": tool_meta["availability"],
                },
            )

        try:
            result = self.adapter.call_tool(tool_name, arguments)
        except BlenderClientError as exc:
            return self._tool_error(
                exc.code,
                str(exc),
                exc.details,
            )
        except Exception as exc:
            return self._tool_error("tool_call_failed", str(exc))

        if isinstance(result, dict) and result.get("error"):
            return self._tool_error(result.get("error", "tool_call_failed"), result.get("message", "Tool call failed"), result)

        text = json.dumps(result, indent=2, ensure_ascii=False)
        return {
            "content": [
                {
                    "type": "text",
                    "text": text,
                }
            ],
            "structuredContent": result,
            "isError": False,
        }

    def _mcp_tool_definition(self, tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": tool["name"],
            "title": self._friendly_title(tool),
            "description": tool["description"],
            "inputSchema": tool["input_schema"],
        }

    def _friendly_title(self, tool: dict[str, Any]) -> str:
        custom_titles = {
            "get_scene_info": "Get Scene Info / Info de Escena",
            "get_object_info": "Get Object Info / Info de Objeto",
            "create_prop_blockout": "Create Prop Blockout / Crear Blockout de Prop",
            "create_environment_layout": "Create Environment Layout / Crear Layout de Entorno",
            "load_character_references": "Load Character References / Cargar Referencias",
            "create_character_blockout": "Create Character Blockout / Crear Blockout de Personaje",
            "capture_character_review": "Capture Character Review / Capturar Revision",
            "compare_character_with_references": "Compare Character with References / Comparar con Referencias",
            "apply_character_proportion_fixes": "Apply Character Proportion Fixes / Corregir Proporciones",
        }
        return custom_titles.get(tool["name"], tool["name"].replace("_", " ").title())

    def _tool_error(self, code: str, message: str, details: Any = None) -> dict[str, Any]:
        payload = {
            "error": code,
            "message": message,
        }
        if details is not None:
            payload["details"] = details
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2, ensure_ascii=False),
                }
            ],
            "structuredContent": payload,
            "isError": True,
        }

    def _write_result(self, request_id: Any, result: dict[str, Any]):
        if request_id is None:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }
        self._write_message(payload)

    def _write_error(self, request_id: Any, code: int, message: str):
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }
        self._write_message(payload)

    def _write_message(self, payload: dict[str, Any]):
        LOGGER.debug("response %s", json.dumps(payload, ensure_ascii=False))
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main():
    MCPStdioServer().run()


if __name__ == "__main__":
    main()
