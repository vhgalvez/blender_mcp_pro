import json
import logging
import os
import sys
from pathlib import Path
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
TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class BlenderMCPAdapter:
    def __init__(self):
        self.client = BlenderTcpClient.from_env()

    def list_tools(self):
        return TOOLS

    def call_tool(self, tool_name: str, params: dict):
        if tool_name not in TOOLS_BY_NAME:
            raise ValueError(f"Unknown tool: {tool_name}")

        params = dict(params or {})
        LOGGER.info(
            "tool_selected %s",
            json.dumps({"tool": tool_name, "params": params}, ensure_ascii=False),
        )

        if tool_name == "list_collections":
            raise NotImplementedError("list_collections is not exposed by the current Blender backend yet")
        if tool_name == "create_character_from_references":
            result = self._create_character_from_references(params)
        elif tool_name == "review_and_fix_character":
            result = self._review_and_fix_character(params)
        elif tool_name == "create_shop_scene":
            result = self._create_shop_scene(params)
        elif tool_name == "create_room_blockout":
            result = self._call_backend(
                "create_environment_layout",
                {
                    "layout_type": "room",
                    "collection_name": params.get("collection_name"),
                },
            )
        elif tool_name == "create_street_blockout":
            result = self._call_backend(
                "create_environment_layout",
                {
                    "layout_type": "corridor",
                    "collection_name": params.get("collection_name"),
                },
            )
        else:
            result = self._call_backend(tool_name, params)

        LOGGER.info(
            "tool_result %s",
            json.dumps({"tool": tool_name, "result": result}, ensure_ascii=False),
        )
        return result

    def route_prompt(self, prompt: str) -> dict:
        original = (prompt or "").strip()
        text = original.lower()
        if not text:
            raise ValueError("Prompt is empty")

        if any(phrase in text for phrase in ["scene info", "scene summary", "show scene", "what is in the scene"]):
            return {"tool": "get_scene_info", "params": {}}

        if text.startswith("object info "):
            return {"tool": "get_object_info", "params": {"name": original[len("object info "):].strip()}}

        if "review the character" in text or "review character" in text:
            return {"tool": "review_and_fix_character", "params": {"strength": 0.35}}

        if "fix character proportions" in text or "fix the character proportions" in text:
            return {"tool": "apply_character_proportion_fixes", "params": {"strength": 0.35}}

        if "create a punk character from references" in text or "create punk character from references" in text:
            return {
                "tool": "create_character_from_references",
                "params": {
                    "reference_dir": "./references",
                    "height": 1.9,
                    "spike_count": 11,
                    "include_metal": True,
                    "add_piercings": True,
                    "blockout_collection_name": "MCP_Punk_Character",
                    "detail_collection_name": "MCP_Punk_Character_Details",
                },
            }

        if "character from references" in text:
            return {
                "tool": "create_character_from_references",
                "params": {
                    "reference_dir": "./references",
                    "height": 1.8,
                    "blockout_collection_name": "MCP_Character",
                    "detail_collection_name": "MCP_Character_Details",
                },
            }

        if "create a table" in text or "create table" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "table", "collection_name": "MCP_Table"}}
        if "create a chair" in text or "create chair" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "chair", "collection_name": "MCP_Chair"}}
        if "create a crate" in text or "create crate" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "crate", "collection_name": "MCP_Crate"}}
        if "create a weapon" in text or "create weapon" in text:
            return {"tool": "create_prop_blockout", "params": {"prop_type": "weapon", "collection_name": "MCP_Weapon"}}

        if "create a small shop scene" in text or "create shop scene" in text or "create a shop scene" in text:
            return {"tool": "create_shop_scene", "params": {"collection_name": "MCP_Shop_Scene"}}

        if "create a bedroom blockout" in text or "create bedroom blockout" in text:
            return {"tool": "create_room_blockout", "params": {"collection_name": "MCP_Bedroom_Blockout"}}

        if "create a room blockout" in text or "create room blockout" in text:
            return {"tool": "create_room_blockout", "params": {"collection_name": "MCP_Room_Blockout"}}

        if "create a street layout" in text or "create street layout" in text or "create street blockout" in text:
            return {"tool": "create_street_blockout", "params": {"collection_name": "MCP_Street_Blockout"}}

        if "apply prop materials" in text or "prop materials" in text:
            return {"tool": "apply_prop_materials", "params": {"include_metal": True}}

        if "apply environment materials" in text or "environment materials" in text:
            return {"tool": "apply_environment_materials", "params": {}}

        if "capture character review" in text or "character review" in text:
            return {"tool": "capture_character_review", "params": {}}

        if "compare character with references" in text or "compare references" in text:
            return {"tool": "compare_character_with_references", "params": {}}

        raise ValueError(f"Could not route prompt: {prompt}")

    def run_character_workflow(self, reference_dir: str):
        LOGGER.info("workflow_start %s", json.dumps({"workflow": "character", "reference_dir": reference_dir}, ensure_ascii=False))
        result = self.call_tool(
            "create_character_from_references",
            {
                "reference_dir": reference_dir,
                "height": 1.8,
                "blockout_collection_name": "MCP_Character_Workflow",
                "detail_collection_name": "MCP_Character_Workflow_Details",
            },
        )
        review = self.call_tool("capture_character_review", {})
        comparison = self.call_tool("compare_character_with_references", {})
        fixes = self.call_tool("apply_character_proportion_fixes", {"strength": 0.35})
        return {
            "workflow": "character",
            "create": result,
            "review": review,
            "comparison": comparison,
            "fixes": fixes,
        }

    def run_environment_workflow(self, scene_type: str):
        scene_type = (scene_type or "").strip().lower()
        LOGGER.info("workflow_start %s", json.dumps({"workflow": "environment", "scene_type": scene_type}, ensure_ascii=False))
        if scene_type in {"shop", "store", "interior shop"}:
            created = self.call_tool("create_shop_scene", {"collection_name": "MCP_Shop_Workflow"})
        elif scene_type in {"room", "bedroom", "interior"}:
            created = self.call_tool("create_room_blockout", {"collection_name": "MCP_Room_Workflow"})
        elif scene_type in {"street", "alley", "corridor"}:
            created = self.call_tool("create_street_blockout", {"collection_name": "MCP_Street_Workflow"})
        else:
            created = self.call_tool("create_environment_layout", {"layout_type": "room", "collection_name": "MCP_Environment_Workflow"})
        materials = self.call_tool("apply_environment_materials", {})
        return {
            "workflow": "environment",
            "create": created,
            "materials": materials,
        }

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
                        "result": self.call_tool(message.get("tool", ""), message.get("params", {}) or {}),
                    }
                else:
                    raise ValueError("Unsupported action")
            except Exception as exc:
                LOGGER.error("adapter_error %s", exc)
                payload = {"ok": False, "error": str(exc)}

            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    def _call_backend(self, tool_name: str, params: dict[str, Any]):
        normalized = self._normalize_params(tool_name, params)
        LOGGER.info(
            "backend_call %s",
            json.dumps({"tool": tool_name, "params": normalized}, ensure_ascii=False),
        )
        return self.client.call(tool_name, normalized)

    def _normalize_params(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {key: value for key, value in params.items() if value is not None}

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

    def _create_character_from_references(self, params: dict[str, Any]):
        reference_paths = self._resolve_reference_inputs(params)
        steps = [
            (
                "load_character_references",
                {
                    "front": reference_paths["front"],
                    "side": reference_paths["side"],
                    "back": reference_paths.get("back"),
                },
            ),
            (
                "create_character_blockout",
                {
                    "height": params.get("height", 1.8),
                    "collection_name": params.get("blockout_collection_name"),
                },
            ),
            (
                "build_character_hair",
                {
                    "spike_count": params.get("spike_count", 9),
                    "collection_name": params.get("detail_collection_name"),
                },
            ),
            (
                "build_character_face",
                {
                    "add_piercings": params.get("add_piercings", False),
                    "collection_name": params.get("detail_collection_name"),
                },
            ),
            (
                "apply_character_materials",
                {
                    "include_metal": params.get("include_metal", False),
                },
            ),
        ]

        results = []
        for tool_name, tool_params in steps:
            results.append({"tool": tool_name, "result": self._call_backend(tool_name, tool_params)})

        return {
            "workflow": "create_character_from_references",
            "notes": "This is a stylized reference-guided Blender workflow, not automatic image-to-3D reconstruction.",
            "steps": results,
        }

    def _review_and_fix_character(self, params: dict[str, Any]):
        strength = params.get("strength", 0.35)
        steps = [
            ("capture_character_review", {}),
            ("compare_character_with_references", {}),
            ("apply_character_proportion_fixes", {"strength": strength}),
        ]
        results = []
        for tool_name, tool_params in steps:
            results.append({"tool": tool_name, "result": self._call_backend(tool_name, tool_params)})
        return {
            "workflow": "review_and_fix_character",
            "steps": results,
        }

    def _create_shop_scene(self, params: dict[str, Any]):
        steps = [
            (
                "create_environment_layout",
                {
                    "layout_type": "shop",
                    "collection_name": params.get("collection_name"),
                },
            ),
            ("apply_environment_materials", {}),
        ]
        results = []
        for tool_name, tool_params in steps:
            results.append({"tool": tool_name, "result": self._call_backend(tool_name, tool_params)})
        return {
            "workflow": "create_shop_scene",
            "steps": results,
        }

    def _resolve_reference_inputs(self, params: dict[str, Any]) -> dict[str, str]:
        front = params.get("front")
        side = params.get("side")
        back = params.get("back")
        reference_dir = params.get("reference_dir")

        if front and side:
            resolved = {"front": front, "side": side}
            if back:
                resolved["back"] = back
            return resolved

        if not reference_dir:
            raise ValueError("create_character_from_references requires either front+side or reference_dir")

        directory = Path(reference_dir).expanduser().resolve()
        if not directory.is_dir():
            raise ValueError(f"reference_dir does not exist or is not a directory: {directory}")

        candidates = [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
        if not candidates:
            raise ValueError(f"No supported image files found in reference_dir: {directory}")

        def first_match(keywords):
            for candidate in candidates:
                name = candidate.stem.lower()
                if any(keyword in name for keyword in keywords):
                    return str(candidate)
            return None

        front = first_match(["front"])
        side = first_match(["side", "profile"])
        back = first_match(["back"])

        if not front or not side:
            raise ValueError(
                "reference_dir must contain at least one front image and one side/profile image"
            )

        resolved = {"front": front, "side": side}
        if back:
            resolved["back"] = back
        return resolved


def route_prompt(prompt: str) -> dict:
    return BlenderMCPAdapter().route_prompt(prompt)


def main():
    BlenderMCPAdapter().serve_stdio()


if __name__ == "__main__":
    main()
