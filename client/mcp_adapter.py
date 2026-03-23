import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from blender_client import BlenderTcpClient
from tools_registry import CALLABLE_TOOL_NAMES, TOOLS, TOOLS_BY_NAME


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
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
LOCAL_WORKFLOW_TOOL_NAMES = {
    "create_character_from_references",
    "review_and_fix_character",
    "create_shop_scene",
}


class BlenderMCPAdapter:
    def __init__(self):
        self.client = BlenderTcpClient.from_env()

    def list_tools(self):
        return TOOLS

    def call_tool(self, tool_name: str, params: dict):
        params = dict(params or {})
        availability = TOOLS_BY_NAME.get(tool_name, {}).get("availability", "local_workflow" if tool_name in LOCAL_WORKFLOW_TOOL_NAMES else "unknown")
        LOGGER.info(
            "tool_selected %s",
            json.dumps(
                {
                    "tool": tool_name,
                    "availability": availability,
                    "params": params,
                },
                ensure_ascii=False,
            ),
        )

        if tool_name in LOCAL_WORKFLOW_TOOL_NAMES:
            if tool_name == "create_character_from_references":
                result = self._create_character_from_references(params)
            elif tool_name == "review_and_fix_character":
                result = self._review_and_fix_character(params)
            else:
                result = self._create_shop_scene(params)
        elif tool_name in TOOLS_BY_NAME:
            tool_meta = TOOLS_BY_NAME[tool_name]
            if tool_meta["availability"] == "unavailable":
                result = {
                    "error": "tool_not_implemented",
                    "tool": tool_name,
                    "message": tool_meta["description"],
                    "suggestions": self._tool_suggestions(tool_name),
                }
                LOGGER.warning("tool_unavailable %s", json.dumps(result, ensure_ascii=False))
                return result
            result = self._call_backend(tool_name, params)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

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

        if any(
            phrase in text
            for phrase in [
                "scene info",
                "scene summary",
                "show scene",
                "what is in the scene",
                "info de escena",
                "resumen de escena",
            ]
        ):
            return {"tool": "get_scene_info", "params": {}}

        if text.startswith("object info "):
            return {"tool": "get_object_info", "params": {"name": original[len("object info ") :].strip()}}
        if text.startswith("info objeto "):
            return {"tool": "get_object_info", "params": {"name": original[len("info objeto ") :].strip()}}

        if any(phrase in text for phrase in ["create a chair", "create chair", "crea una silla", "crear una silla"]):
            return {"tool": "create_prop_blockout", "params": {"prop_type": "chair", "collection_name": "MCP_Chair"}}
        if any(phrase in text for phrase in ["create a table", "create table", "create prop table", "crea una mesa", "crear una mesa"]):
            return {"tool": "create_prop_blockout", "params": {"prop_type": "table", "collection_name": "MCP_Table"}}

        if any(
            phrase in text
            for phrase in [
                "create punk character from references",
                "create a punk character from references",
                "create punk character",
                "create a punk character",
                "crea un personaje punk",
                "crear un personaje punk",
            ]
        ):
            return {
                "tool": "create_character_from_references",
                "params": {
                    "reference_dir": "./references",
                    "height": 1.9,
                    "spike_count": 11,
                    "add_piercings": True,
                    "include_metal": True,
                    "blockout_collection_name": "MCP_Punk_Character",
                    "detail_collection_name": "MCP_Punk_Character_Details",
                },
            }

        if any(
            phrase in text
            for phrase in [
                "review character",
                "review the character",
                "review character against references",
                "revisa el personaje",
                "revisa personaje",
            ]
        ):
            return {"tool": "review_and_fix_character", "params": {"strength": 0.35}}

        if any(
            phrase in text
            for phrase in [
                "fix proportions",
                "fix character proportions",
                "arregla proporciones",
                "arregla las proporciones",
                "corrige proporciones",
            ]
        ):
            return {"tool": "apply_character_proportion_fixes", "params": {"strength": 0.35}}

        if any(
            phrase in text
            for phrase in [
                "create shop scene",
                "create a small shop scene",
                "create a shop scene",
                "crea una escena de tienda",
                "crea una tienda",
            ]
        ):
            return {"tool": "create_shop_scene", "params": {"collection_name": "MCP_Shop_Scene"}}

        if any(
            phrase in text
            for phrase in [
                "create bedroom blockout",
                "create a bedroom blockout",
                "crea un dormitorio",
                "crea un bloque de dormitorio",
                "crea una habitación",
                "crea una habitacion",
            ]
        ):
            return {"tool": "create_environment_layout", "params": {"layout_type": "room", "collection_name": "MCP_Bedroom_Blockout"}}

        if any(
            phrase in text
            for phrase in [
                "create room blockout",
                "create environment layout",
                "room layout",
                "environment layout",
                "crea un cuarto",
                "crea un layout de entorno",
                "layout de entorno",
            ]
        ):
            return {"tool": "create_environment_layout", "params": {"layout_type": "room", "collection_name": "MCP_Room_Blockout"}}

        if any(
            phrase in text
            for phrase in [
                "create street layout",
                "create street blockout",
                "create a street layout",
                "create a street blockout",
                "crea una calle",
                "crea un layout de calle",
                "crea un bloque de calle",
            ]
        ):
            return {
                "error": "tool_not_implemented",
                "suggestions": self._tool_suggestions("create_street_blockout"),
            }

        raise ValueError(f"Could not route prompt: {prompt}")

    def run_character_workflow(self, reference_dir: str):
        LOGGER.info(
            "workflow_start %s",
            json.dumps({"workflow": "character", "reference_dir": reference_dir}, ensure_ascii=False),
        )
        created = self.call_tool(
            "create_character_from_references",
            {
                "reference_dir": reference_dir,
                "height": 1.9,
                "spike_count": 11,
                "add_piercings": True,
                "include_metal": True,
                "blockout_collection_name": "MCP_Punk_Character",
                "detail_collection_name": "MCP_Punk_Character_Details",
            },
        )
        review = self.call_tool("capture_character_review", {})
        comparison = self.call_tool("compare_character_with_references", {})
        fixes = self.call_tool("apply_character_proportion_fixes", {"strength": 0.35})
        return {
            "workflow": "character",
            "create": created,
            "review": review,
            "comparison": comparison,
            "fixes": fixes,
        }

    def run_environment_workflow(self, scene_type: str):
        scene_type = (scene_type or "").strip().lower()
        LOGGER.info(
            "workflow_start %s",
            json.dumps({"workflow": "environment", "scene_type": scene_type}, ensure_ascii=False),
        )
        if scene_type in {"shop", "store", "tienda"}:
            created = self.call_tool("create_shop_scene", {"collection_name": "MCP_Shop_Workflow"})
        elif scene_type in {"room", "bedroom", "interior", "cuarto", "habitacion", "habitación", "dormitorio"}:
            created = self.call_tool("create_environment_layout", {"layout_type": "room", "collection_name": "MCP_Room_Workflow"})
        else:
            return {
                "error": "tool_not_implemented",
                "message": "Environment workflow currently supports room/bedroom and shop. Street is not implemented server-side.",
                "suggestions": self._tool_suggestions("create_street_blockout"),
            }
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
        if tool_name not in CALLABLE_TOOL_NAMES:
            raise ValueError(f"Tool is not implemented on the Blender server: {tool_name}")
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

        if tool_name in {
            "create_prop_blockout",
            "apply_prop_symmetry",
            "apply_prop_materials",
        }:
            params.setdefault("mode", "props")

        if tool_name in {
            "create_environment_layout",
            "apply_environment_materials",
        }:
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
                    "height": params.get("height", 1.9),
                    "collection_name": params.get("blockout_collection_name"),
                },
            ),
            (
                "build_character_hair",
                {
                    "spike_count": params.get("spike_count", 11),
                    "collection_name": params.get("detail_collection_name"),
                },
            ),
            (
                "build_character_face",
                {
                    "add_piercings": params.get("add_piercings", True),
                    "collection_name": params.get("detail_collection_name"),
                },
            ),
            (
                "apply_character_materials",
                {
                    "include_metal": params.get("include_metal", True),
                },
            ),
        ]

        results = []
        for step_name, step_params in steps:
            results.append({"tool": step_name, "result": self._call_backend(step_name, step_params)})

        return {
            "workflow": "create_character_from_references",
            "notes": "This is a stylized reference-guided Blender workflow. It does not perform automatic image-to-3D reconstruction.",
            "steps": results,
        }

    def _review_and_fix_character(self, params: dict[str, Any]):
        strength = float(params.get("strength", 0.35))
        steps = [
            ("capture_character_review", {}),
            ("compare_character_with_references", {}),
            ("apply_character_proportion_fixes", {"strength": strength}),
        ]
        results = []
        for step_name, step_params in steps:
            results.append({"tool": step_name, "result": self._call_backend(step_name, step_params)})
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
        for step_name, step_params in steps:
            results.append({"tool": step_name, "result": self._call_backend(step_name, step_params)})
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
                stem = candidate.stem.lower()
                if any(keyword in stem for keyword in keywords):
                    return str(candidate)
            return None

        front = first_match(["front", "frente"])
        side = first_match(["side", "profile", "perfil", "lateral"])
        back = first_match(["back", "espalda", "trasera", "posterior"])

        if not front or not side:
            raise ValueError("reference_dir must contain at least one front image and one side/profile image")

        resolved = {"front": front, "side": side}
        if back:
            resolved["back"] = back
        return resolved

    def _tool_suggestions(self, tool_name: str):
        if tool_name == "list_collections":
            return ["get_scene_info", "get_object_info"]
        if tool_name == "create_street_blockout":
            return [
                {"tool": "create_environment_layout", "params": {"layout_type": "corridor", "collection_name": "MCP_Corridor_Blockout"}},
                {"tool": "create_environment_layout", "params": {"layout_type": "room", "collection_name": "MCP_Room_Blockout"}},
                {"tool": "create_environment_layout", "params": {"layout_type": "shop", "collection_name": "MCP_Shop_Scene"}},
            ]
        return []


def route_prompt(prompt: str) -> dict:
    return BlenderMCPAdapter().route_prompt(prompt)


def main():
    BlenderMCPAdapter().serve_stdio()


if __name__ == "__main__":
    main()
