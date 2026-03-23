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
        "title": "Review / Get Scene Info",
        "domain": "review/refinement",
        "description": "Return a summary of the current Blender scene.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "get_scene_info",
        "build_params": lambda arguments: {},
    },
    "get_object_info": {
        "title": "Review / Get Object Info",
        "domain": "review/refinement",
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
    "load_character_references": {
        "title": "Character / Load References",
        "domain": "character",
        "description": "Load front and side character reference images, with an optional back image.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "front": {
                    "type": "string",
                    "description": "Safe local path to the front reference image.",
                },
                "side": {
                    "type": "string",
                    "description": "Safe local path to the side reference image.",
                },
                "back": {
                    "type": "string",
                    "description": "Optional safe local path to the back reference image.",
                },
            },
            "required": ["front", "side"],
        },
        "command": "load_character_references",
        "build_params": lambda arguments: build_load_character_references_params(arguments),
    },
    "clear_character_references": {
        "title": "Character / Clear References",
        "domain": "character",
        "description": "Remove the currently loaded character reference planes.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "clear_character_references",
        "build_params": lambda arguments: {"mode": "character"},
    },
    "create_character_blockout": {
        "title": "Character / Create Blockout",
        "domain": "character",
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
    "apply_character_symmetry": {
        "title": "Character / Apply Symmetry",
        "domain": "character",
        "description": "Apply a mirror setup to the current character meshes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of mesh object names to target. Defaults to character meshes.",
                },
                "use_bisect": {
                    "type": "boolean",
                    "description": "Whether to bisect on the mirror axis.",
                },
                "use_clip": {
                    "type": "boolean",
                    "description": "Whether to enable mirror clipping.",
                },
            },
        },
        "command": "apply_character_symmetry",
        "build_params": lambda arguments: build_apply_character_symmetry_params(arguments),
    },
    "build_character_hair": {
        "title": "Character / Build Hair",
        "domain": "character",
        "description": "Build a simple stylized hair blockout for the active character setup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spike_count": {
                    "type": "integer",
                    "description": "Number of stylized hair spikes. Defaults to 9.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
        },
        "command": "build_character_hair",
        "build_params": lambda arguments: build_character_hair_params(arguments),
    },
    "build_character_face": {
        "title": "Character / Build Face",
        "domain": "character",
        "description": "Build stylized face details for the active character blockout.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "add_piercings": {
                    "type": "boolean",
                    "description": "Whether to add simple piercings to the stylized face setup.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
        },
        "command": "build_character_face",
        "build_params": lambda arguments: build_character_face_params(arguments),
    },
    "apply_character_materials": {
        "title": "Character / Apply Materials",
        "domain": "character",
        "description": "Apply basic character materials to the current character blockout.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_metal": {
                    "type": "boolean",
                    "description": "Whether to include metallic accents.",
                }
            },
        },
        "command": "apply_character_materials",
        "build_params": lambda arguments: build_apply_character_materials_params(arguments),
    },
    "capture_character_review": {
        "title": "Review / Capture Character Review",
        "domain": "review/refinement",
        "description": "Capture front and side review screenshots of the current character.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "capture_character_review",
        "build_params": lambda arguments: {"mode": "character"},
    },
    "compare_character_with_references": {
        "title": "Review / Compare Character With References",
        "domain": "review/refinement",
        "description": "Compare the current character against loaded references using simple silhouette heuristics.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "compare_character_with_references",
        "build_params": lambda arguments: {"mode": "character"},
    },
    "apply_character_proportion_fixes": {
        "title": "Review / Apply Character Proportion Fixes",
        "domain": "review/refinement",
        "description": "Apply proportion adjustments from a correction report or explicit deltas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "correction_report": {
                    "type": "object",
                    "description": "Optional correction report returned by compare_character_with_references.",
                },
                "deltas": {
                    "type": "object",
                    "description": "Optional explicit deltas keyed by proportion field.",
                },
                "strength": {
                    "type": "number",
                    "description": "Blend strength from 0.0 to 1.0. Defaults to 1.0.",
                },
            },
        },
        "command": "apply_character_proportion_fixes",
        "build_params": lambda arguments: build_apply_character_proportion_fixes_params(arguments),
    },
    "create_character_from_references": {
        "title": "Character / Create From References",
        "domain": "character",
        "description": "Run a basic image-guided stylized character setup sequence using loaded references, blockout, hair, face, and materials.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "front": {
                    "type": "string",
                    "description": "Safe local path to the front reference image.",
                },
                "side": {
                    "type": "string",
                    "description": "Safe local path to the side reference image.",
                },
                "back": {
                    "type": "string",
                    "description": "Optional safe local path to the back reference image.",
                },
                "height": {
                    "type": "number",
                    "description": "Character height in Blender units. Defaults to 2.0.",
                },
                "blockout_collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name for the character blockout.",
                },
                "detail_collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name for hair and face detail objects.",
                },
                "spike_count": {
                    "type": "integer",
                    "description": "Optional number of hair spikes. Defaults to backend behavior.",
                },
                "add_piercings": {
                    "type": "boolean",
                    "description": "Whether to add simple face piercings.",
                },
                "include_metal": {
                    "type": "boolean",
                    "description": "Whether to include metallic accents in materials.",
                },
            },
            "required": ["front", "side"],
        },
        "handler": "create_character_from_references",
    },
    "create_prop_blockout": {
        "title": "Props / Create Prop Blockout",
        "domain": "props",
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
    "apply_prop_materials": {
        "title": "Props / Apply Materials",
        "domain": "props",
        "description": "Apply simple prop materials to the current prop blockout.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_metal": {
                    "type": "boolean",
                    "description": "Whether to include metallic materials where relevant.",
                }
            },
        },
        "command": "apply_prop_materials",
        "build_params": lambda arguments: build_apply_prop_materials_params(arguments),
    },
    "create_environment_layout": {
        "title": "Environment / Create Layout",
        "domain": "environment",
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
    "apply_environment_materials": {
        "title": "Environment / Apply Materials",
        "domain": "environment",
        "description": "Apply simple materials to the current environment layout.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "apply_environment_materials",
        "build_params": lambda arguments: {"mode": "environment"},
    },
    "get_polyhaven_status": {
        "title": "Integrations / Get Poly Haven Status",
        "domain": "integrations",
        "description": "Check whether the Blender backend currently has Poly Haven integration enabled.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "command": "get_polyhaven_status",
        "build_params": lambda arguments: {},
    },
    "search_polyhaven_assets": {
        "title": "Integrations / Search Poly Haven Assets",
        "domain": "integrations",
        "description": "Search Poly Haven assets through the existing Blender backend integration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "Optional asset type hint such as hdri, texture, or model.",
                },
                "categories": {
                    "type": "string",
                    "description": "Optional comma-separated category filter.",
                },
            },
        },
        "command": "search_polyhaven_assets",
        "build_params": lambda arguments: build_search_polyhaven_assets_params(arguments),
    },
    "download_polyhaven_asset": {
        "title": "Integrations / Download Poly Haven Asset",
        "domain": "integrations",
        "description": "Download and import a Poly Haven asset through the Blender backend.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Poly Haven asset identifier.",
                },
                "asset_type": {
                    "type": "string",
                    "description": "Asset type such as hdri, texture, or model.",
                },
                "resolution": {
                    "type": "string",
                    "description": "Optional target resolution such as 1k, 2k, or 4k.",
                },
                "file_format": {
                    "type": "string",
                    "description": "Optional file format hint supported by the backend integration.",
                },
            },
            "required": ["asset_id", "asset_type"],
        },
        "command": "download_polyhaven_asset",
        "build_params": lambda arguments: build_download_polyhaven_asset_params(arguments),
    },
    "set_texture": {
        "title": "Integrations / Set Texture",
        "domain": "integrations",
        "description": "Apply a previously imported texture set to a Blender object by name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "Target Blender object name.",
                },
                "texture_id": {
                    "type": "string",
                    "description": "Texture identifier previously imported into Blender.",
                },
            },
            "required": ["object_name", "texture_id"],
        },
        "command": "set_texture",
        "build_params": lambda arguments: build_set_texture_params(arguments),
    },
    "review_and_fix_character": {
        "title": "Review / Review And Fix Character",
        "domain": "review/refinement",
        "description": "Capture review screenshots, compare against references, and apply proportion fixes in one compact sequence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strength": {
                    "type": "number",
                    "description": "Blend strength from 0.0 to 1.0 for the fix pass. Defaults to 0.35.",
                }
            },
        },
        "handler": "review_and_fix_character",
    },
    "create_shop_scene": {
        "title": "Environment / Create Shop Scene",
        "domain": "environment",
        "description": "Create a shop environment layout and apply environment materials in one compact sequence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name for the shop layout.",
                }
            },
        },
        "handler": "create_shop_scene",
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


def build_load_character_references_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "mode": "character",
        "front": require_string(arguments, "front"),
        "side": require_string(arguments, "side"),
    }
    back = optional_string(arguments, "back")
    if back is not None:
        params["back"] = back
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


def build_character_hair_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "character"}
    spike_count = arguments.get("spike_count")
    if spike_count is not None:
        if not isinstance(spike_count, int):
            raise ValueError("'spike_count' must be an integer")
        params["spike_count"] = spike_count
    collection_name = optional_string(arguments, "collection_name")
    if collection_name is not None:
        params["collection_name"] = collection_name
    return params


def build_apply_character_symmetry_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "character"}
    object_names = arguments.get("object_names")
    if object_names is not None:
        if not isinstance(object_names, list) or not all(isinstance(name, str) for name in object_names):
            raise ValueError("'object_names' must be an array of strings")
        params["object_names"] = object_names
    use_bisect = arguments.get("use_bisect")
    if use_bisect is not None:
        if not isinstance(use_bisect, bool):
            raise ValueError("'use_bisect' must be a boolean")
        params["use_bisect"] = use_bisect
    use_clip = arguments.get("use_clip")
    if use_clip is not None:
        if not isinstance(use_clip, bool):
            raise ValueError("'use_clip' must be a boolean")
        params["use_clip"] = use_clip
    return params


def build_character_face_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "character"}
    add_piercings = arguments.get("add_piercings")
    if add_piercings is not None:
        if not isinstance(add_piercings, bool):
            raise ValueError("'add_piercings' must be a boolean")
        params["add_piercings"] = add_piercings
    collection_name = optional_string(arguments, "collection_name")
    if collection_name is not None:
        params["collection_name"] = collection_name
    return params


def build_apply_character_materials_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "character"}
    include_metal = arguments.get("include_metal")
    if include_metal is not None:
        if not isinstance(include_metal, bool):
            raise ValueError("'include_metal' must be a boolean")
        params["include_metal"] = include_metal
    return params


def build_apply_prop_materials_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "props"}
    include_metal = arguments.get("include_metal")
    if include_metal is not None:
        if not isinstance(include_metal, bool):
            raise ValueError("'include_metal' must be a boolean")
        params["include_metal"] = include_metal
    return params


def build_apply_character_proportion_fixes_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"mode": "character"}
    correction_report = arguments.get("correction_report")
    if correction_report is not None:
        if not isinstance(correction_report, dict):
            raise ValueError("'correction_report' must be an object")
        params["correction_report"] = correction_report
    deltas = arguments.get("deltas")
    if deltas is not None:
        if not isinstance(deltas, dict):
            raise ValueError("'deltas' must be an object")
        params["deltas"] = deltas
    strength = arguments.get("strength")
    if strength is not None:
        if not isinstance(strength, (int, float)):
            raise ValueError("'strength' must be a number")
        params["strength"] = float(strength)
    return params


def build_search_polyhaven_assets_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    asset_type = optional_string(arguments, "asset_type")
    if asset_type is not None:
        params["asset_type"] = asset_type
    categories = optional_string(arguments, "categories")
    if categories is not None:
        params["categories"] = categories
    return params


def build_download_polyhaven_asset_params(arguments: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "asset_id": require_string(arguments, "asset_id"),
        "asset_type": require_string(arguments, "asset_type"),
    }
    resolution = optional_string(arguments, "resolution")
    if resolution is not None:
        params["resolution"] = resolution
    file_format = optional_string(arguments, "file_format")
    if file_format is not None:
        params["file_format"] = file_format
    return params


def build_set_texture_params(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_name": require_string(arguments, "object_name"),
        "texture_id": require_string(arguments, "texture_id"),
    }


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
                    "title": spec.get("title"),
                    "description": spec["description"],
                    "inputSchema": spec["inputSchema"],
                    "_meta": {"domain": spec.get("domain")},
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
        try:
            client = self.get_client()
            if "handler" in spec:
                LOGGER.info("Calling MCP workflow tool=%s params=%s", name, arguments)
                result = getattr(self, spec["handler"])(client, arguments)
            else:
                command_params = spec["build_params"](arguments)
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

    def create_character_from_references(self, client: BlenderTcpClient, arguments: dict[str, Any]) -> dict[str, Any]:
        load_params = build_load_character_references_params(arguments)
        blockout_params = build_character_params(
            {
                "height": arguments.get("height"),
                "collection_name": arguments.get("blockout_collection_name"),
            }
        )
        hair_params = build_character_hair_params(
            {
                "spike_count": arguments.get("spike_count"),
                "collection_name": arguments.get("detail_collection_name"),
            }
        )
        face_params = build_character_face_params(
            {
                "add_piercings": arguments.get("add_piercings"),
                "collection_name": arguments.get("detail_collection_name"),
            }
        )
        material_params = build_apply_character_materials_params(
            {"include_metal": arguments.get("include_metal")}
        )

        steps = [
            ("load_character_references", load_params),
            ("create_character_blockout", blockout_params),
            ("build_character_hair", hair_params),
            ("build_character_face", face_params),
            ("apply_character_materials", material_params),
        ]

        results: list[dict[str, Any]] = []
        for command, command_params in steps:
            LOGGER.info("Workflow step command=%s params=%s", command, command_params)
            step_result = client.call(command, command_params)
            results.append({"command": command, "result": step_result})

        return {
            "success": True,
            "workflow": "create_character_from_references",
            "notes": (
                "This workflow creates a stylized character setup guided by reference images. "
                "It does not perform automatic ML-based image-to-3D reconstruction."
            ),
            "steps": results,
        }

    def review_and_fix_character(self, client: BlenderTcpClient, arguments: dict[str, Any]) -> dict[str, Any]:
        strength = arguments.get("strength", 0.35)
        if not isinstance(strength, (int, float)):
            raise ValueError("'strength' must be a number")

        steps = [
            ("capture_character_review", {"mode": "character"}),
            ("compare_character_with_references", {"mode": "character"}),
            ("apply_character_proportion_fixes", {"mode": "character", "strength": float(strength)}),
        ]
        results: list[dict[str, Any]] = []
        for command, command_params in steps:
            LOGGER.info("Workflow step command=%s params=%s", command, command_params)
            step_result = client.call(command, command_params)
            results.append({"command": command, "result": step_result})
        return {
            "success": True,
            "workflow": "review_and_fix_character",
            "steps": results,
        }

    def create_shop_scene(self, client: BlenderTcpClient, arguments: dict[str, Any]) -> dict[str, Any]:
        create_params = build_environment_params(
            {
                "layout_type": "shop",
                "collection_name": arguments.get("collection_name"),
            }
        )
        steps = [
            ("create_environment_layout", create_params),
            ("apply_environment_materials", {"mode": "environment"}),
        ]
        results: list[dict[str, Any]] = []
        for command, command_params in steps:
            LOGGER.info("Workflow step command=%s params=%s", command, command_params)
            step_result = client.call(command, command_params)
            results.append({"command": command, "result": step_result})
        return {
            "success": True,
            "workflow": "create_shop_scene",
            "steps": results,
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
