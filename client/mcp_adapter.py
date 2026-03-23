import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from blender_client import BlenderTcpClient
from tools_registry import CALLABLE_TOOL_NAMES, SERVER_TOOL_NAMES, TOOLS, TOOLS_BY_NAME, WORKFLOW_TOOL_NAMES


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


class BlenderMCPAdapter:
    def __init__(self):
        self.client = BlenderTcpClient.from_env()

    def list_tools(self):
        return TOOLS

    def call_tool(self, tool_name: str, params: dict):
        params = dict(params or {})
        availability = TOOLS_BY_NAME.get(tool_name, {}).get("availability", "unknown")
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

        if tool_name in WORKFLOW_TOOL_NAMES:
            if tool_name == "create_character_from_references":
                result = self._create_character_from_references(params)
            elif tool_name == "review_and_fix_character":
                result = self._review_and_fix_character(params)
            elif tool_name == "create_shop_scene":
                result = self._create_shop_scene(params)
            elif tool_name == "generate_scene_plan":
                result = self._generate_scene_plan(params)
            elif tool_name == "apply_scene_plan":
                result = self._apply_scene_plan(params)
            elif tool_name == "build_scene_from_description":
                result = self._build_scene_from_description(params)
            elif tool_name == "build_character_from_description":
                result = self._build_character_from_description(params)
            elif tool_name == "import_asset":
                result = self._import_asset(params)
            else:
                raise ValueError(f"Unsupported workflow tool: {tool_name}")
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

        if any(
            phrase in text
            for phrase in [
                "create a chair",
                "create chair",
                "create a chair in blender",
                "crea una silla",
                "crear una silla",
                "crea una silla en blender",
            ]
        ):
            return {"tool": "create_prop_blockout", "params": {"prop_type": "chair", "collection_name": "MCP_Chair"}}
        if any(
            phrase in text
            for phrase in [
                "create a table",
                "create table",
                "create a table in blender",
                "create prop table",
                "crea una mesa",
                "crear una mesa",
                "crea una mesa en blender",
            ]
        ):
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
        ) or (("character" in text or "personaje" in text) and "punk" in text):
            return {"tool": "build_character_from_description", "params": {"description": original, "style": "stylized punk cartoon"}}

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
                "create a stylized bedroom",
                "create a bedroom",
                "create a room",
                "create a small shop",
                "create a shop",
                "crea una habitación",
                "crea una habitacion",
                "crea una tienda",
                "hazme una tienda",
                "hazme una habitación",
            ]
        ) or any(keyword in text for keyword in ["bedroom", "dormitorio", "habitación", "habitacion", "room", "tienda", "shop"]):
            return {"tool": "build_scene_from_description", "params": {"description": original}}

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
        if tool_name not in SERVER_TOOL_NAMES:
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

    def _generate_scene_plan(self, params: dict[str, Any]):
        description = str(params.get("description", "")).strip()
        style = str(params.get("style", "")).strip() or "default"
        if not description:
            raise ValueError("description is required")

        text = description.lower()
        plan = {
            "description": description,
            "style": style,
            "environment": None,
            "props": [],
            "primitives": [],
            "materials": [],
            "lights": [],
            "camera": None,
            "limitations": [],
        }

        if any(keyword in text for keyword in ["shop", "tienda", "store"]):
            plan["environment"] = {"layout_type": "shop", "collection_name": "MCP_Generated_Shop"}
        elif any(keyword in text for keyword in ["bedroom", "room", "habitación", "habitacion", "cuarto", "dormitorio"]):
            plan["environment"] = {"layout_type": "room", "collection_name": "MCP_Generated_Room"}
        elif any(keyword in text for keyword in ["corridor", "hallway", "pasillo"]):
            plan["environment"] = {"layout_type": "corridor", "collection_name": "MCP_Generated_Corridor"}

        if "chair" in text or "silla" in text:
            plan["props"].append({"prop_type": "chair", "collection_name": "MCP_Generated_Props"})
        if "table" in text or "mesa" in text or "desk" in text or "escritorio" in text:
            plan["props"].append({"prop_type": "table", "collection_name": "MCP_Generated_Props"})
        if "crate" in text or "caja" in text:
            plan["props"].append({"prop_type": "crate", "collection_name": "MCP_Generated_Props"})
        if "weapon" in text or "sword" in text or "arma" in text:
            plan["props"].append({"prop_type": "weapon", "collection_name": "MCP_Generated_Props"})
        if "plane" in text or "airplane" in text or "avión" in text or "avion" in text:
            plan["props"].append({"prop_type": "plane", "collection_name": "MCP_Generated_Props"})

        if "lamp" in text or "lámpara" in text or "lampara" in text:
            plan["lights"].append({"light_type": "POINT", "name": "MCP_Lamp", "location": [2.0, -2.0, 3.0], "energy": 1500.0})
        if "sunset" in text or "atardecer" in text:
            plan["lights"].append({"light_type": "SUN", "name": "MCP_Sunset_Sun", "rotation": [0.9, 0.0, 0.6], "energy": 2.5, "color": [1.0, 0.65, 0.45]})
        elif not plan["lights"]:
            plan["lights"].append({"light_type": "SUN", "name": "MCP_Key_Sun", "rotation": [0.9, 0.0, 0.8], "energy": 2.0, "color": [1.0, 0.95, 0.9]})

        if "bed" in text or "cama" in text:
            plan["primitives"].extend(
                [
                    {"primitive_type": "cube", "name": "MCP_Bed_Base", "location": [0.0, -0.6, 0.25], "scale": [1.2, 2.0, 0.25]},
                    {"primitive_type": "cube", "name": "MCP_Bed_Headboard", "location": [0.0, -1.6, 0.8], "scale": [1.2, 0.08, 0.8]},
                ]
            )
        if "shelf" in text or "estantería" in text or "estanteria" in text:
            plan["primitives"].append({"primitive_type": "cube", "name": "MCP_Shelf_Block", "location": [2.0, -1.5, 1.0], "scale": [0.25, 0.9, 1.0]})
        if "counter" in text or "mostrador" in text:
            plan["primitives"].append({"primitive_type": "cube", "name": "MCP_Counter_Block", "location": [0.0, 1.2, 0.6], "scale": [1.5, 0.4, 0.6]})

        plan["camera"] = {"name": "MCP_Camera", "location": [7.0, -7.0, 5.0], "rotation": [1.0, 0.0, 0.8], "lens": 45.0, "make_active": True}

        if plan["environment"] is None and not plan["props"] and not plan["primitives"]:
            return {
                "error": "tool_not_implemented",
                "message": "The description could not be mapped to the current safe scene-building tools.",
                "suggestions": [
                    "Try asking for a room, shop, corridor, chair, table, bed, shelf, counter, lamp, or sunset lighting.",
                ],
            }

        if "street" in text or "calle" in text:
            plan["limitations"].append("Street scenes are not implemented as a dedicated layout; corridor is the closest supported layout.")

        return {"success": True, "plan": plan}

    def _apply_scene_plan(self, params: dict[str, Any]):
        plan = params.get("plan")
        if not isinstance(plan, dict):
            raise ValueError("plan must be an object")

        steps = []

        environment = plan.get("environment")
        if environment:
            steps.append({"tool": "create_environment_layout", "result": self._call_backend("create_environment_layout", environment)})
            steps.append({"tool": "apply_environment_materials", "result": self._call_backend("apply_environment_materials", {})})

        for prop in plan.get("props", []):
            steps.append({"tool": "create_prop_blockout", "result": self._call_backend("create_prop_blockout", prop)})

        if plan.get("props"):
            steps.append({"tool": "apply_prop_materials", "result": self._call_backend("apply_prop_materials", {"include_metal": False})})

        for primitive in plan.get("primitives", []):
            steps.append({"tool": "create_primitive", "result": self._call_backend("create_primitive", primitive)})

        for light in plan.get("lights", []):
            steps.append({"tool": "create_light", "result": self._call_backend("create_light", light)})

        camera = plan.get("camera")
        if camera:
            steps.append({"tool": "set_camera", "result": self._call_backend("set_camera", camera)})

        return {
            "workflow": "apply_scene_plan",
            "description": plan.get("description", ""),
            "style": plan.get("style", ""),
            "limitations": plan.get("limitations", []),
            "steps": steps,
        }

    def _build_scene_from_description(self, params: dict[str, Any]):
        generated = self._generate_scene_plan(params)
        if generated.get("error"):
            return generated
        return self._apply_scene_plan({"plan": generated["plan"]})

    def _build_character_from_description(self, params: dict[str, Any]):
        description = str(params.get("description", "")).strip()
        style = str(params.get("style", "")).strip() or "stylized"
        if not description:
            raise ValueError("description is required")

        text = description.lower()
        spike_count = 11 if "punk" in text or "spiky" in text or "pinchos" in text else 7
        height = 1.9 if "big head" in text or "cabeza grande" in text else 1.8
        include_metal = any(keyword in text for keyword in ["punk", "metal", "chain", "cadena"])
        add_piercings = any(keyword in text for keyword in ["piercing", "piercings", "punk"])

        steps = [
            {"tool": "create_character_blockout", "result": self._call_backend("create_character_blockout", {"height": height, "collection_name": "MCP_Generated_Character"})},
            {"tool": "build_character_hair", "result": self._call_backend("build_character_hair", {"spike_count": spike_count, "collection_name": "MCP_Generated_Character_Details"})},
            {"tool": "build_character_face", "result": self._call_backend("build_character_face", {"add_piercings": add_piercings, "collection_name": "MCP_Generated_Character_Details"})},
            {"tool": "apply_character_materials", "result": self._call_backend("apply_character_materials", {"include_metal": include_metal})},
        ]

        if any(keyword in text for keyword in ["thin limbs", "thin arms", "thin legs", "extremidades finas", "brazos delgados", "piernas delgadas"]):
            steps.append({"tool": "apply_character_proportion_fixes", "result": self._call_backend("apply_character_proportion_fixes", {"deltas": {"arm_thickness": {"delta": -0.18}, "leg_thickness": {"delta": -0.15}}, "strength": 0.7})})

        return {
            "workflow": "build_character_from_description",
            "description": description,
            "style": style,
            "limitations": ["This builds a stylized procedural character blockout; it does not perform automatic image-to-3D reconstruction."],
            "steps": steps,
        }

    def _import_asset(self, params: dict[str, Any]):
        source = params.get("source")
        if source == "polyhaven":
            required = {"asset_id", "asset_type"}
            missing = sorted(name for name in required if not params.get(name))
            if missing:
                raise ValueError(f"Missing required params for polyhaven import_asset: {missing}")
            return self._call_backend(
                "download_polyhaven_asset",
                {
                    "asset_id": params["asset_id"],
                    "asset_type": params["asset_type"],
                    "resolution": params.get("resolution"),
                    "file_format": params.get("file_format"),
                },
            )
        if source == "sketchfab":
            if not params.get("uid"):
                raise ValueError("Missing required param for sketchfab import_asset: uid")
            return self._call_backend(
                "download_sketchfab_model",
                {
                    "uid": params["uid"],
                    "normalize_size": bool(params.get("normalize_size", False)),
                    "target_size": float(params.get("target_size", 1.0)),
                },
            )
        return {
            "error": "tool_not_implemented",
            "message": f"Unsupported asset source: {source}",
            "suggestions": ["polyhaven", "sketchfab"],
        }

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
