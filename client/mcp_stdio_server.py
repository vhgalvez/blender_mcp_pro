import json
import logging
import os
import sys
from datetime import date
from typing import Any

from blender_client import BlenderClientError
from mcp_adapter import BlenderMCPAdapter
from tools_registry import CALLABLE_TOOLS, TOOLS_BY_NAME


SERVER_NAME = "blender-mcp-pro"
SERVER_VERSION = "1.1.0"

# Ordered newest-first so initialize can pick the best mutual date-based version.
SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
)

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603

SERVER_NOT_INITIALIZED = -32002
SERVER_SHUTDOWN = -32000


def configure_logging() -> logging.Logger:
    level_name = os.environ.get(
        "BLENDER_MCP_STDIO_LOG",
        os.environ.get("BLENDER_MCP_ADAPTER_LOG", "INFO"),
    ).upper()
    level = getattr(logging, level_name, logging.INFO)

    # Stdio transport must keep stdout reserved for JSON-RPC messages only.
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("blender_mcp_stdio_server")


LOGGER = configure_logging()

SUPPORTED_PROTOCOL_DATES = tuple(date.fromisoformat(version) for version in SUPPORTED_PROTOCOL_VERSIONS)
LATEST_SUPPORTED_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]


class MCPStdioServer:
    def __init__(self) -> None:
        self.adapter = BlenderMCPAdapter()
        self.initialize_completed = False
        self.client_initialized = False
        self.shutdown_requested = False
        self.exit_requested = False
        self.negotiated_protocol_version: str | None = None
        self.client_info: dict[str, Any] = {}
        self.client_capabilities: dict[str, Any] = {}

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
            except Exception as exc:
                LOGGER.error("invalid_json error=%s", exc)
                self._write_error(None, JSONRPC_PARSE_ERROR, f"Parse error: {exc}")
                continue

            if not isinstance(message, dict):
                LOGGER.error("invalid_message_type type=%s", type(message).__name__)
                self._write_error(None, JSONRPC_INVALID_REQUEST, "Invalid Request: message must be an object")
                continue

            LOGGER.debug("request %s", json.dumps(message, ensure_ascii=False))
            self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]) -> None:
        is_request = "id" in message
        request_id = message.get("id")
        jsonrpc = message.get("jsonrpc")
        method = message.get("method")
        params = message.get("params")

        if jsonrpc != "2.0":
            self._write_error_if_request(
                is_request,
                request_id,
                JSONRPC_INVALID_REQUEST,
                "Invalid Request: jsonrpc must be '2.0'",
            )
            return

        if not isinstance(method, str) or not method:
            self._write_error_if_request(
                is_request,
                request_id,
                JSONRPC_INVALID_REQUEST,
                "Invalid Request: method must be a non-empty string",
            )
            return

        if params is None:
            params = {}

        if not isinstance(params, dict):
            self._write_error_if_request(
                is_request,
                request_id,
                JSONRPC_INVALID_PARAMS,
                "Invalid params: params must be an object",
            )
            return

        try:
            if method == "initialize":
                self._handle_initialize(is_request, request_id, params)
                return

            if method == "ping":
                if is_request:
                    self._write_result(request_id, {})
                return

            if method == "notifications/initialized":
                self._handle_initialized_notification()
                return

            if method == "shutdown":
                self._handle_shutdown(is_request, request_id)
                return

            if method == "exit":
                self._handle_exit()
                return

            if self.shutdown_requested:
                self._write_error_if_request(
                    is_request,
                    request_id,
                    SERVER_SHUTDOWN,
                    "Server is shut down and only 'exit' is allowed",
                )
                return

            if not self.client_initialized:
                self._write_error_if_request(
                    is_request,
                    request_id,
                    SERVER_NOT_INITIALIZED,
                    "Server not initialized",
                )
                return

            if method == "tools/list":
                self._handle_tools_list(is_request, request_id)
                return

            if method == "tools/call":
                self._handle_tools_call(is_request, request_id, params)
                return

            if is_request:
                self._write_error(request_id, JSONRPC_METHOD_NOT_FOUND, f"Method not found: {method}")
            else:
                LOGGER.info("ignored_notification method=%s", method)
        except Exception as exc:
            LOGGER.exception("request_failed method=%s", method)
            self._write_error_if_request(
                is_request,
                request_id,
                JSONRPC_INTERNAL_ERROR,
                str(exc),
            )

    def _handle_initialize(self, is_request: bool, request_id: Any, params: dict[str, Any]) -> None:
        if not is_request:
            LOGGER.warning("ignored_initialize_notification")
            return

        if self.initialize_completed and not self.shutdown_requested:
            self._write_error(
                request_id,
                JSONRPC_INVALID_REQUEST,
                "Initialize may only be called once per session",
            )
            return

        client_protocol_version = params.get("protocolVersion")
        client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})

        if not isinstance(client_protocol_version, str):
            self._write_error(
                request_id,
                JSONRPC_INVALID_PARAMS,
                "Invalid params: protocolVersion must be a string",
            )
            return

        if client_capabilities is None:
            client_capabilities = {}
        if client_info is None:
            client_info = {}

        if not isinstance(client_capabilities, dict):
            self._write_error(
                request_id,
                JSONRPC_INVALID_PARAMS,
                "Invalid params: capabilities must be an object",
            )
            return

        if not isinstance(client_info, dict):
            self._write_error(
                request_id,
                JSONRPC_INVALID_PARAMS,
                "Invalid params: clientInfo must be an object",
            )
            return

        negotiated = self._negotiate_protocol_version(client_protocol_version)
        if negotiated is None:
            self._write_error(
                request_id,
                JSONRPC_INVALID_PARAMS,
                f"Unsupported protocol version: {client_protocol_version}",
            )
            return

        self.negotiated_protocol_version = negotiated
        self.client_info = client_info
        self.client_capabilities = client_capabilities
        self.initialize_completed = True
        self.client_initialized = False
        self.shutdown_requested = False
        self.exit_requested = False

        LOGGER.info(
            "initialize client_protocol=%s negotiated_protocol=%s client_info=%s",
            client_protocol_version,
            negotiated,
            json.dumps(self.client_info, ensure_ascii=False),
        )

        self._write_result(
            request_id,
            {
                "protocolVersion": negotiated,
                "capabilities": self._server_capabilities(),
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

    def _handle_initialized_notification(self) -> None:
        if not self.initialize_completed:
            LOGGER.warning("initialized_notification_before_initialize")
            return

        if self.shutdown_requested:
            LOGGER.warning("initialized_notification_after_shutdown")
            return

        self.client_initialized = True
        LOGGER.info(
            "client_initialized negotiated_protocol=%s",
            self.negotiated_protocol_version,
        )

    def _handle_shutdown(self, is_request: bool, request_id: Any) -> None:
        if not is_request:
            LOGGER.info("ignored_shutdown_notification")
            return

        if not self.initialize_completed:
            self._write_error(request_id, SERVER_NOT_INITIALIZED, "Server not initialized")
            return

        # MCP stdio shutdown is usually stream closure; keep LSP-style shutdown/exit
        # as a compatibility path for hosts that still send those messages.
        self.shutdown_requested = True
        self.client_initialized = False
        self._write_result(request_id, {})

    def _handle_exit(self) -> None:
        self.exit_requested = True
        LOGGER.info("exit_requested shutdown=%s", self.shutdown_requested)

    def _handle_tools_list(self, is_request: bool, request_id: Any) -> None:
        if not is_request:
            LOGGER.info("ignored_tools_list_notification")
            return

        tools = [self._mcp_tool_definition(tool) for tool in CALLABLE_TOOLS]
        LOGGER.info("tools_list count=%s", len(tools))
        self._write_result(request_id, {"tools": tools})

    def _handle_tools_call(self, is_request: bool, request_id: Any, params: dict[str, Any]) -> None:
        if not is_request:
            LOGGER.info("ignored_tools_call_notification")
            return

        tool_name = params.get("name")
        arguments = params.get("arguments")

        if arguments is None:
            arguments = {}

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
        # MCP versions are calendar strings; prefer the exact match, otherwise
        # negotiate to the newest server version that does not exceed the client.
        try:
            client_date = date.fromisoformat(client_version)
        except ValueError:
            return None

        if client_version in SUPPORTED_PROTOCOL_VERSIONS:
            return client_version

        for supported_version, supported_date in zip(
            SUPPORTED_PROTOCOL_VERSIONS,
            SUPPORTED_PROTOCOL_DATES,
            strict=True,
        ):
            if supported_date <= client_date:
                return supported_version

        return LATEST_SUPPORTED_PROTOCOL_VERSION

    def _server_capabilities(self) -> dict[str, Any]:
        return {
            "tools": {
                "listChanged": False,
            },
        }

    def _write_error_if_request(
        self,
        is_request: bool,
        request_id: Any,
        code: int,
        message: str,
    ) -> None:
        if is_request:
            self._write_error(request_id, code, message)
        else:
            LOGGER.warning("notification_error code=%s message=%s", code, message)

    def _write_result(self, request_id: Any, result: dict[str, Any]) -> None:
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
