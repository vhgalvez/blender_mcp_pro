import json
import logging
import os
import sys
import traceback
from typing import Any

from blender_client import BlenderClientError, BlenderTcpClient


PROTOCOL_VERSION = "2025-11-25"
SERVER_INFO = {
    "name": "blender-mcp-bridge",
    "version": "1.0.0",
}


def configure_logging() -> logging.Logger:
    level_name = os.environ.get("BLENDER_MCP_BRIDGE_LOG", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("blender_mcp_bridge")


LOGGER = configure_logging()

TOOLS = {
    "get_scene_info": {
        "description": "Return a summary of the current Blender scene.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "get_scene_info",
        "build_params": lambda arguments: {},
    },
    "get_object_info": {
        "description": "Return transform and mesh details for a Blender object by name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The Blender object name.",
                }
            },
            "required": ["name"],
        },
        "command": "get_object_info",
        "build_params": lambda arguments: {"name": require_string(arguments, "name")},
    },
    "create_character_blockout": {
        "description": "Create a simple character blockout in the current Blender scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "height": {
                    "type": "number",
                    "description": "Character height in Blender units. Defaults to 2.0.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
        },
        "command": "create_character_blockout",
        "build_params": lambda arguments: build_character_params(arguments),
    },
    "create_prop_blockout": {
        "description": "Create a prop blockout for a supported prop type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prop_type": {
                    "type": "string",
                    "enum": ["chair", "table", "crate", "weapon"],
                    "description": "Supported prop archetype.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "required": ["prop_type"],
        },
        "command": "create_prop_blockout",
        "build_params": lambda arguments: build_prop_params(arguments),
    },
    "create_environment_layout": {
        "description": "Create a simple environment layout for a supported layout type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layout_type": {
                    "type": "string",
                    "enum": ["room", "corridor", "shop", "kiosk"],
                    "description": "Supported environment archetype.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "required": ["layout_type"],
        },
        "command": "create_environment_layout",
        "build_params": lambda arguments: build_environment_params(arguments),
    },
}


def require_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string")
    return value


def optional_string(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string when provided")
    return value


def build_character_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "character"}
    height = arguments.get("height")
    if height is not None:
        if not isinstance(height, (int, float)):
            raise ValueError("'height' must be a number")
        params["height"] = float(height)
    collection_name = optional_string(arguments, "collection_name")
    if collection_name is not None:
        params["collection_name"] = collection_name
    return params


def build_prop_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params = {
        "mode": "props",
        "prop_type": require_string(arguments, "prop_type"),
    }
    collection_name = optional_string(arguments, "collection_name")
    if collection_name is not None:
        params["collection_name"] = collection_name
    return params


def build_environment_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params = {
        "mode": "environment",
        "layout_type": require_string(arguments, "layout_type"),
    }
    collection_name = optional_string(arguments, "collection_name")
    if collection_name is not None:
        params["collection_name"] = collection_name
    return params


class McpBridgeServer:
    def __init__(self):
        self.client: BlenderTcpClient | None = None
        self.initialized = False
        self.client_init_error: str | None = None

    def serve(self) -> None:
        LOGGER.info("Starting MCP STDIO bridge")
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                self.send_error(None, -32700, "Parse error", {"details": str(exc)})
                continue

            if not isinstance(message, dict):
                self.send_error(None, -32600, "Invalid Request")
                continue

            if "id" in message:
                self.handle_request(message)
            else:
                self.handle_notification(message)

    def handle_request(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        if message.get("jsonrpc") != "2.0":
            self.send_error(request_id, -32600, "Invalid Request")
            return

        method = message.get("method")
        params = message.get("params") or {}
        LOGGER.info("Received MCP request method=%s id=%s", method, request_id)
        if not isinstance(params, dict):
            self.send_error(request_id, -32602, "Invalid params")
            return

        try:
            if method == "initialize":
                self.send_result(
                    request_id,
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": SERVER_INFO,
                        "instructions": (
                            "This MCP bridge forwards tool calls to the Blender MCP Pro add-on over the "
                            "existing local authenticated TCP socket."
                        ),
                    },
                )
                return

            if method == "ping":
                self.send_result(request_id, {})
                return

            if not self.initialized:
                self.send_error(request_id, -32002, "Server not initialized")
                return

            if method == "tools/list":
                self.send_result(request_id, {"tools": self.list_tools()})
                return

            if method == "tools/call":
                self.send_result(request_id, self.call_tool(params))
                return

            self.send_error(request_id, -32601, f"Method not found: {method}")
        except ValueError as exc:
            LOGGER.warning("Request validation failed method=%s id=%s error=%s", method, request_id, exc)
            self.send_error(request_id, -32602, "Invalid params", {"details": str(exc)})
        except Exception as exc:
            LOGGER.exception("Unhandled MCP request error method=%s id=%s", method, request_id)
            self.send_error(request_id, -32603, "Internal error", {"details": str(exc)})

    def handle_notification(self, message: dict[str, Any]) -> None:
        if message.get("jsonrpc") != "2.0":
            return
        if message.get("method") == "notifications/initialized":
            self.initialized = True
            LOGGER.info("MCP client initialized")

    def get_client(self) -> BlenderTcpClient:
        if self.client is not None:
            return self.client
        if self.client_init_error is not None:
            raise RuntimeError(self.client_init_error)
        try:
            self.client = BlenderTcpClient.from_env()
            LOGGER.info(
                "Configured Blender backend target host=%s port=%s env_vars=BLENDER_HOST,BLENDER_PORT,BLENDER_TOKEN",
                self.client.host,
                self.client.port,
            )
            return self.client
        except Exception as exc:
            self.client_init_error = str(exc)
            LOGGER.error("Invalid Blender bridge configuration: %s", exc)
            raise

    def list_tools(self) -> list[dict[str, Any]]:
        tools = []
        for name, spec in TOOLS.items():
            tools.append(
                {
                    "name": name,
                    "description": spec["description"],
                    "inputSchema": spec["inputSchema"],
                }
            )
        return tools

    def call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str) or name not in TOOLS:
            raise ValueError("Unknown tool name")

        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise ValueError("'arguments' must be an object")

        spec = TOOLS[name]
        command_params = spec["build_params"](arguments)
        try:
            client = self.get_client()
            LOGGER.info("Calling MCP tool=%s backend_command=%s params=%s", name, spec["command"], command_params)
            result = client.call(spec["command"], command_params)
        except BlenderClientError as exc:
            LOGGER.warning("Backend tool failure tool=%s code=%s message=%s", name, exc.code, exc)
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"{exc.code}: {exc}",
                    }
                ],
                "structuredContent": {
                    "ok": False,
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                        "details": exc.details,
                    },
                },
            }
        except OSError as exc:
            LOGGER.warning("Backend connection failure tool=%s error=%s", name, exc)
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"Could not reach Blender TCP backend at {client.host}:{client.port}: {exc}",
                    }
                ],
                "structuredContent": {
                    "ok": False,
                    "error": {
                        "code": "connection_failed",
                        "message": str(exc),
                    },
                },
            }
        except Exception as exc:
            LOGGER.error("Bridge tool failure tool=%s error=%s", name, exc)
            LOGGER.debug("Bridge tool traceback:\n%s", traceback.format_exc())
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"Bridge error while calling {name}: {exc}",
                    }
                ],
                "structuredContent": {
                    "ok": False,
                    "error": {
                        "code": "bridge_error",
                        "message": str(exc),
                    },
                },
            }

        LOGGER.info("MCP tool succeeded tool=%s", name)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2),
                }
            ],
            "structuredContent": result,
        }

    def send_result(self, request_id: Any, result: dict[str, Any]) -> None:
        self.send_message({"jsonrpc": "2.0", "id": request_id, "result": result})

    def send_error(self, request_id: Any, code: int, message: str, data: dict[str, Any] | None = None) -> None:
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        self.send_message({"jsonrpc": "2.0", "id": request_id, "error": error})

    def send_message(self, payload: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main() -> None:
    McpBridgeServer().serve()


if __name__ == "__main__":
    main()
