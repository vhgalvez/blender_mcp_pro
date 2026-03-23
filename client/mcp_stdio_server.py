import json
import logging
import os
import sys
from typing import Any

from blender_client import BlenderClientError
from mcp_adapter import BlenderMCPAdapter
from tools_registry import CALLABLE_TOOLS, TOOLS_BY_NAME


SERVER_NAME = "blender-mcp-pro"
SERVER_VERSION = "1.1.0"

# Keep this conservative for current interoperability.
# MCP version negotiation happens during initialize.
SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-06-18",
    "2025-03-26",
)


def configure_logging() -> logging.Logger:
    level_name = os.environ.get(
        "BLENDER_MCP_STDIO_LOG",
        os.environ.get("BLENDER_MCP_ADAPTER_LOG", "INFO"),
    ).upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("blender_mcp_stdio_server")


LOGGER = configure_logging()


class MCPStdioServer:
    def __init__(self) -> None:
        self.adapter = BlenderMCPAdapter()
        self.initialized = False
        self.shutdown_requested = False
        self.exit_requested = False
        self.negotiated_protocol_version: str | None = None
        self.client_info: dict[str, Any] | None = None

    def run(self) -> None:
        LOGGER.info(
            "stdio_server_started name=%s version=%s supported_protocols=%s",
            SERVER_NAME,
            SERVER_VERSION,
            ",".join(SUPPORTED_PROTOCOL_VERSIONS),
        )

        while not self.exit_requested:
            raw_line = sys.stdin.readline()
            if raw_line == "":
                LOGGER.info("stdin_closed")
                break

            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("MCP message must be a JSON object")
            except Exception as exc:
                LOGGER.error("invalid_json error=%s", exc)
                self._write_error(None, -32700, f"Parse error: {exc}")
                continue

            LOGGER.debug("request %s", json.dumps(message, ensure_ascii=False))
            self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]) -> None:
        jsonrpc = message.get("jsonrpc")
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params", {}) or {}

        if jsonrpc != "2.0":
            self._write_error(request_id, -32600, "Invalid Request: jsonrpc must be '2.0'")
            return

        if not isinstance(params, dict):
            self._write_error(request_id, -32602, "Invalid params: params must be an object")
            return

        try:
            # Lifecycle: initialize must happen first.
            if method == "initialize":
                self._handle_initialize(request_id, params)
                return

            if method == "notifications/initialized":
                if not self.initialized:
                    LOGGER.warning("initialized_notification_before_initialize")
                return

            if method == "shutdown":
                if not self.initialized:
                    self._write_error(request_id, -32002, "Server not initialized")
                    return
                self.shutdown_requested = True
                self._write_result(request_id, {})
                return

            if method == "exit":
                self.exit_requested = True
                return

            # After shutdown, only exit should be accepted.
            if self.shutdown_requested:
                self._write_error(
                    request_id,
                    -32000,
                    "Server is shut down and only 'exit' is allowed",
                )
                return

            if not self.initialized:
                self._write_error(request_id, -32002, "Server not initialized")
                return

            if method == "ping":
                self._write_result(request_id, {})
                return

            if method == "tools/list":
                self._handle_tools_list(request_id)
                return

            if method == "tools/call":
                self._handle_tools_call(request_id, params)
                return

            self._write_error(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:
            LOGGER.exception("request_failed method=%s", method)
            self._write_error(request_id, -32000, str(exc))

    def _handle_initialize(self, request_id: Any, params: dict[str, Any]) -> None:
        client_protocol_version = params.get("protocolVersion")
        client_info = params.get("clientInfo", {})

        if not isinstance(client_protocol_version, str):
            self._write_error(
                request_id,
                -32602,
                "Invalid params: protocolVersion must be a string",
            )
            return

        negotiated = self._negotiate_protocol_version(client_protocol_version)
        if negotiated is None:
            self._write_error(
                request_id,
                -32000,
                f"Unsupported protocol version: {client_protocol_version}",
            )
            return

        self.negotiated_protocol_version = negotiated
        self.client_info = client_info if isinstance(client_info, dict) else {}
        self.initialized = True
        self.shutdown_requested = False

        LOGGER.info(
            "initialized client_protocol=%s negotiated_protocol=%s client_info=%s",
            client_protocol_version,
            negotiated,
            json.dumps(self.client_info, ensure_ascii=False),
        )

        self._write_result(
            request_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    },
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "instructions": (
                    "Use the available Blender tools to inspect scenes, create props, "
                    "and build higher-level scene workflows through the MCP bridge."
                ),
            },
        )

    def _handle_tools_list(self, request_id: Any) -> None:
        tools = [self._mcp_tool_definition(tool) for tool in CALLABLE_TOOLS]
        LOGGER.info("tools_list count=%s", len(tools))
        self._write_result(request_id, {"tools": tools})

    def _handle_tools_call(self, request_id: Any, params: dict[str, Any]) -> None:
        tool_name = params.get("name")
        arguments = params.get("arguments", {}) or {}

        if not isinstance(tool_name, str) or not tool_name.strip():
            self._write_result(
                request_id,
                self._tool_error("missing_tool_name", "Tool name is required."),
            )
            return

        if not isinstance(arguments, dict):
            self._write_result(
                request_id,
                self._tool_error("invalid_arguments", "Tool arguments must be an object."),
            )
            return

        LOGGER.info(
            "tool_call name=%s arguments=%s",
            tool_name,
            json.dumps(arguments, ensure_ascii=False),
        )
        result = self._call_tool(tool_name, arguments)
        self._write_result(request_id, result)

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool_meta = TOOLS_BY_NAME.get(tool_name)
        if not tool_meta:
            return self._tool_error("unknown_tool", f"Unknown tool: {tool_name}")

        if tool_meta.get("availability") == "unavailable":
            return self._tool_error(
                "tool_not_implemented",
                tool_meta.get("description", "This tool is currently unavailable."),
                {
                    "tool": tool_name,
                    "availability": tool_meta.get("availability"),
                },
            )

        try:
            result = self.adapter.call_tool(tool_name, arguments)
        except BlenderClientError as exc:
            LOGGER.warning("tool_call_backend_error name=%s code=%s", tool_name, exc.code)
            return self._tool_error(exc.code, str(exc), exc.details)
        except Exception as exc:
            LOGGER.exception("tool_call_failed name=%s", tool_name)
            return self._tool_error("tool_call_failed", str(exc))

        if isinstance(result, dict) and result.get("error"):
            return self._tool_error(
                str(result.get("error", "tool_call_failed")),
                str(result.get("message", "Tool call failed")),
                result,
            )

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
        return tool["name"].replace("_", " ").title()

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

    def _negotiate_protocol_version(self, client_version: str) -> str | None:
        if client_version in SUPPORTED_PROTOCOL_VERSIONS:
            return client_version

        # Graceful fallback for common MCP clients.
        # If the client sends something unsupported, we reject it explicitly.
        return None

    def _write_result(self, request_id: Any, result: dict[str, Any]) -> None:
        if request_id is None:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }
        self._write_message(payload)

    def _write_error(self, request_id: Any, code: int, message: str) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }
        self._write_message(payload)

    def _write_message(self, payload: dict[str, Any]) -> None:
        LOGGER.debug("response %s", json.dumps(payload, ensure_ascii=False))
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main() -> None:
    try:
        MCPStdioServer().run()
    except KeyboardInterrupt:
        LOGGER.info("stdio_server_interrupted")
    except Exception:
        LOGGER.exception("stdio_server_fatal")
        raise


if __name__ == "__main__":
    main()