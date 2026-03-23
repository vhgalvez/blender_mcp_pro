import json
import logging
import os
import sys
from typing import Any

from blender_client import BlenderTcpClient
from tools_registry import TOOLS


def configure_logging() -> logging.Logger:
    level_name = os.environ.get("BLENDER_MCP_ADAPTER_LOG", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("blender_mcp_adapter")


LOGGER = configure_logging()

TOOL_NAMES = {tool["name"] for tool in TOOLS}


class BlenderMCPAdapter:
    def __init__(self):
        self.client = BlenderTcpClient.from_env()

    def list_tools(self):
        return TOOLS

    def call_tool(self, tool_name: str, params: dict):
        if tool_name not in TOOL_NAMES:
            raise ValueError(f"Unknown tool: {tool_name}")
        normalized = self._normalize_params(tool_name, dict(params or {}))
        LOGGER.info(
            "tool_call %s",
            json.dumps(
                {
                    "tool": tool_name,
                    "params": normalized,
                },
                ensure_ascii=False,
            ),
        )
        response = self.client.call(tool_name, normalized)
        LOGGER.info(
            "tool_response %s",
            json.dumps(
                {
                    "tool": tool_name,
                    "response": response,
                },
                ensure_ascii=False,
            ),
        )
        return response

    def route_prompt(self, prompt: str) -> dict:
        text = (prompt or "").strip().lower()
        if not text:
            raise ValueError("Prompt is empty")

        if "scene info" in text or "show scene" in text or "scene summary" in text:
            return {"tool": "get_scene_info", "params": {}}

        if text.startswith("object info "):
            return {"tool": "get_object_info", "params": {"name": prompt[len("object info "):].strip()}}

        if "create table" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "table", "collection_name": "MCP_Table", "mode": "props"}}
        if "create chair" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "chair", "collection_name": "MCP_Chair", "mode": "props"}}
        if "create crate" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "crate", "collection_name": "MCP_Crate", "mode": "props"}}
        if "create weapon" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "weapon", "collection_name": "MCP_Weapon", "mode": "props"}}

        if "prop materials" in text:
            return {"tool": "apply_prop_materials", "params": {"mode": "props"}}

        if "create shop" in text:
            return {"tool": "create_environment_layout", "params": {"layout_type": "shop", "collection_name": "MCP_Shop", "mode": "environment"}}
        if "create room" in text:
            return {"tool": "create_environment_layout", "params": {"layout_type": "room", "collection_name": "MCP_Room", "mode": "environment"}}
        if "environment materials" in text or "apply environment materials" in text:
            return {"tool": "apply_environment_materials", "params": {"mode": "environment"}}

        if "character blockout" in text:
            return {"tool": "create_character_blockout", "params": {"mode": "character", "height": 1.8, "collection_name": "MCP_Character"}}
        if "character hair" in text or "build hair" in text:
            return {"tool": "build_character_hair", "params": {"mode": "character", "spike_count": 9}}
        if "character face" in text or "build face" in text:
            return {"tool": "build_character_face", "params": {"mode": "character", "add_piercings": False}}
        if "character materials" in text:
            return {"tool": "apply_character_materials", "params": {"mode": "character"}}
        if "character review" in text or "capture review" in text:
            return {"tool": "capture_character_review", "params": {"mode": "character"}}
        if "compare character" in text or "compare references" in text:
            return {"tool": "compare_character_with_references", "params": {"mode": "character"}}

        raise ValueError(f"Could not route prompt: {prompt}")

    def serve_stdio(self):
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("Message must be a JSON object")

                action = message.get("action")
                if action == "list_tools":
                    payload = {"ok": True, "tools": self.list_tools()}
                elif action == "route_prompt":
                    payload = {"ok": True, "call": self.route_prompt(message.get("prompt", ""))}
                elif action == "call_tool":
                    payload = {
                        "ok": True,
                        "result": self.call_tool(
                            message.get("tool", ""),
                            message.get("params", {}) or {},
                        ),
                    }
                else:
                    raise ValueError("Unsupported action")
            except Exception as exc:
                payload = {"ok": False, "error": str(exc)}

            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    def _normalize_params(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool_name in {
            "load_character_references",
            "clear_character_references",
            "create_character_blockout",
            "apply_character_symmetry",
            "build_character_hair",
            "build_character_face",
            "apply_character_materials",
            "capture_character_review",
            "compare_character_with_references",
            "apply_character_proportion_fixes",
        }:
            params.setdefault("mode", "character")

        if tool_name in {"create_prop_blockout", "apply_prop_materials"}:
            params.setdefault("mode", "props")

        if tool_name in {"create_environment_layout", "apply_environment_materials"}:
            params.setdefault("mode", "environment")

        return params


def route_prompt(prompt: str) -> dict:
    return BlenderMCPAdapter().route_prompt(prompt)


def main():
    BlenderMCPAdapter().serve_stdio()


if __name__ == "__main__":
    main()
