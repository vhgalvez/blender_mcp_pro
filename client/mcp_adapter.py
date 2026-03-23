import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from blender_client import BlenderTcpClient
from tools_registry import CALLABLE_TOOL_NAMES, TOOLS, TOOLS_BY_NAME, WORKFLOW_TOOL_NAMES


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
SCENE_KEYWORDS = {
    "room",
    "bedroom",
    "shop",
    "store",
    "corridor",
    "kiosk",
    "habitacion",
    "habitación",
    "cuarto",
    "dormitorio",
    "tienda",
    "pasillo",
    "escena",
}
CHARACTER_KEYWORDS = {"character", "personaje", "avatar"}
CREATE_WORDS = {"create", "build", "make", "crea", "crear", "hazme", "construye"}


class BlenderMCPAdapter:
    def __init__(self):
        self.client = BlenderTcpClient.from_env()

    def list_tools(self):
        return TOOLS

    def call_tool(self, tool_name: str, params: dict | None):
        if tool_name not in CALLABLE_TOOL_NAMES:
            raise ValueError(f"Unknown tool: {tool_name}")

        params = dict(params or {})
        LOGGER.info("tool_call %s", json.dumps({"tool": tool_name, "params": params}, ensure_ascii=False))

        if tool_name in WORKFLOW_TOOL_NAMES:
            result = self._call_workflow(tool_name, params)
        else:
            result = self._call_backend(tool_name, params)

        LOGGER.info("tool_result %s", json.dumps({"tool": tool_name, "result": result}, ensure_ascii=False))
        return result

    def route_prompt(self, prompt: str) -> dict[str, Any]:
        original = (prompt or "").strip()
        text = original.lower()
        if not text:
            raise ValueError("Prompt is empty")

        if any(phrase in text for phrase in {"scene info", "scene summary", "info de escena", "resumen de escena"}):
            return {"tool": "scene_info", "params": {}}

        object_match = re.match(r"^(object info|info objeto)\s+(.+)$", original, re.IGNORECASE)
        if object_match:
            return {"tool": "object_info", "params": {"name": object_match.group(2).strip()}}

        if any(phrase in text for phrase in {"screenshot", "captura", "screenshot viewport", "captura viewport"}):
            return {"tool": "viewport_screenshot", "params": {}}

        if "reference" in text or "referencia" in text:
            return {"tool": "create_character_from_references", "params": {}}

        if ("review" in text or "revisa" in text or "corrige" in text) and any(keyword in text for keyword in CHARACTER_KEYWORDS):
            return {"tool": "review_and_fix_character", "params": {"strength": 0.35}}

        if any(keyword in text for keyword in CHARACTER_KEYWORDS):
            return {"tool": "build_character_from_description", "params": {"description": original}}

        if any(keyword in text for keyword in SCENE_KEYWORDS) or (
            any(word in text.split() for word in CREATE_WORDS)
            and any(keyword in text for keyword in {"chair", "table", "bed", "silla", "mesa", "cama", "desk", "escritorio", "counter", "mostrador"})
        ):
            return {"tool": "build_scene_from_description", "params": {"description": original}}

        return self._limitation(
            "unroutable_prompt",
            "The prompt could not be mapped to the current primitive or generative tool set.",
            suggestions=[
                "scene_info",
                "build_scene_from_description",
                "build_character_from_description",
                "search_assets",
            ],
        )

    def run_character_workflow(self, reference_dir: str):
        return self.call_tool("create_character_from_references", {"reference_dir": reference_dir})

    def run_environment_workflow(self, description: str):
        return self.call_tool("build_scene_from_description", {"description": description})

    def _call_backend(self, tool_name: str, params: dict[str, Any]):
        tool = TOOLS_BY_NAME[tool_name]
        backend_command = tool["backend_command"]
        normalized = self._normalize_backend_params(backend_command, params)
        return self.client.call(backend_command, normalized)

    def _normalize_backend_params(self, backend_command: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {key: value for key, value in params.items() if value is not None}

        if backend_command in {
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

        if backend_command in {"create_prop_blockout", "apply_prop_symmetry", "apply_prop_materials"}:
            params.setdefault("mode", "props")

        if backend_command in {"create_environment_layout", "apply_environment_materials"}:
            params.setdefault("mode", "environment")

        return params

    def _call_workflow(self, tool_name: str, params: dict[str, Any]):
        workflows = {
            "search_assets": self._search_assets,
            "import_asset": self._import_asset,
            "generate_scene_plan": self._generate_scene_plan,
            "apply_scene_plan": self._apply_scene_plan,
            "build_scene_from_description": self._build_scene_from_description,
            "build_character_from_description": self._build_character_from_description,
            "create_character_from_references": self._create_character_from_references,
            "review_and_fix_character": self._review_and_fix_character,
        }
        return workflows[tool_name](params)

    def _search_assets(self, params: dict[str, Any]):
        source = str(params.get("source", "")).strip().lower()
        if source == "polyhaven":
            return self.client.call(
                "search_polyhaven_assets",
                {
                    "asset_type": params.get("asset_type"),
                    "categories": params.get("categories"),
                },
            )
        if source == "sketchfab":
            query = str(params.get("query", "")).strip()
            if not query:
                raise ValueError("query is required for source='sketchfab'")
            return self.client.call(
                "search_sketchfab_models",
                {
                    "query": query,
                    "categories": params.get("categories"),
                    "count": params.get("count", 20),
                    "downloadable": bool(params.get("downloadable", True)),
                },
            )
        return self._limitation("unsupported_source", f"Unsupported asset source: {source}", suggestions=["polyhaven", "sketchfab"])

    def _import_asset(self, params: dict[str, Any]):
        source = str(params.get("source", "")).strip().lower()
        if source == "polyhaven":
            required = {"asset_id", "asset_type"}
            missing = sorted(name for name in required if not params.get(name))
            if missing:
                raise ValueError(f"Missing required params for polyhaven import: {missing}")
            return self.client.call(
                "download_polyhaven_asset",
                {
                    "asset_id": params["asset_id"],
                    "asset_type": params["asset_type"],
                    "resolution": params.get("resolution"),
                    "file_format": params.get("file_format"),
                },
            )
        if source == "sketchfab":
            uid = str(params.get("uid", "")).strip()
            if not uid:
                raise ValueError("uid is required for source='sketchfab'")
            return self.client.call(
                "download_sketchfab_model",
                {
                    "uid": uid,
                    "normalize_size": bool(params.get("normalize_size", False)),
                    "target_size": float(params.get("target_size", 1.0)),
                },
            )
        return self._limitation("unsupported_source", f"Unsupported asset source: {source}", suggestions=["polyhaven", "sketchfab"])

    def _generate_scene_plan(self, params: dict[str, Any]):
        description = str(params.get("description", "")).strip()
        style = str(params.get("style", "")).strip() or "default"
        use_assets = bool(params.get("use_assets", False))
        if not description:
            raise ValueError("description is required")

        text = description.lower()
        plan = {
            "description": description,
            "style": style,
            "use_assets": use_assets,
            "environment": None,
            "props": [],
            "primitives": [],
            "lights": [],
            "camera": {
                "name": "MCP_Camera",
                "location": [7.0, -7.0, 5.0],
                "rotation": [1.0, 0.0, 0.8],
                "lens": 45.0,
                "make_active": True,
            },
            "limitations": [],
        }

        if any(keyword in text for keyword in {"shop", "store", "tienda"}):
            plan["environment"] = {"layout_type": "shop", "collection_name": "MCP_Generated_Shop"}
        elif any(keyword in text for keyword in {"corridor", "hallway", "pasillo"}):
            plan["environment"] = {"layout_type": "corridor", "collection_name": "MCP_Generated_Corridor"}
        elif any(keyword in text for keyword in {"room", "bedroom", "habitacion", "habitación", "cuarto", "dormitorio"}):
            plan["environment"] = {"layout_type": "room", "collection_name": "MCP_Generated_Room"}

        prop_keywords = {
            "chair": "chair",
            "silla": "chair",
            "table": "table",
            "mesa": "table",
            "desk": "table",
            "escritorio": "table",
            "crate": "crate",
            "caja": "crate",
            "weapon": "weapon",
            "sword": "weapon",
            "arma": "weapon",
            "plane": "plane",
            "airplane": "plane",
            "avion": "plane",
            "avión": "plane",
        }
        selected_props = []
        for keyword, prop_type in prop_keywords.items():
            if keyword in text and prop_type not in selected_props:
                selected_props.append(prop_type)
                plan["props"].append({"prop_type": prop_type, "collection_name": "MCP_Generated_Props"})

        if "bed" in text or "cama" in text:
            plan["primitives"].extend(
                [
                    {"primitive_type": "cube", "name": "MCP_Bed_Base", "location": [0.0, -0.6, 0.25], "scale": [1.2, 2.0, 0.25]},
                    {"primitive_type": "cube", "name": "MCP_Bed_Headboard", "location": [0.0, -1.6, 0.8], "scale": [1.2, 0.08, 0.8]},
                ]
            )
        if "counter" in text or "mostrador" in text:
            plan["primitives"].append({"primitive_type": "cube", "name": "MCP_Counter_Block", "location": [0.0, 1.2, 0.6], "scale": [1.5, 0.4, 0.6]})
        if "shelf" in text or "shelves" in text or "estanteria" in text or "estantería" in text:
            plan["primitives"].append({"primitive_type": "cube", "name": "MCP_Shelf_Block", "location": [2.0, -1.5, 1.0], "scale": [0.25, 0.9, 1.0]})

        if any(keyword in text for keyword in {"warm", "calida", "cálida", "sunset", "atardecer"}):
            plan["lights"].append(
                {
                    "light_type": "SUN",
                    "name": "MCP_Warm_Sun",
                    "rotation": [0.9, 0.0, 0.6],
                    "energy": 2.5,
                    "color": [1.0, 0.72, 0.48],
                }
            )
        else:
            plan["lights"].append(
                {
                    "light_type": "SUN",
                    "name": "MCP_Key_Sun",
                    "rotation": [0.9, 0.0, 0.8],
                    "energy": 2.0,
                    "color": [1.0, 0.95, 0.9],
                }
            )

        if "lamp" in text or "lampara" in text or "lámpara" in text:
            plan["lights"].append(
                {
                    "light_type": "POINT",
                    "name": "MCP_Practical_Lamp",
                    "location": [2.0, -2.0, 3.0],
                    "energy": 1400.0,
                    "color": [1.0, 0.9, 0.75],
                }
            )

        if use_assets:
            plan["limitations"].append("Automatic asset selection is limited to explicit provider calls through search_assets/import_asset.")
        if "street" in text or "calle" in text:
            plan["limitations"].append("Dedicated street layouts are not implemented; corridor is the closest supported environment primitive.")

        if plan["environment"] is None and not plan["props"] and not plan["primitives"]:
            return self._limitation(
                "scene_plan_not_supported",
                "The description could not be mapped to the current safe scene-building primitives.",
                suggestions=["room", "shop", "corridor", "chair", "table", "bed", "counter", "shelf"],
            )

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
        reference_mode = str(params.get("reference_mode", "")).strip()
        if not description:
            raise ValueError("description is required")

        text = description.lower()
        spike_count = 11 if any(keyword in text for keyword in {"punk", "spiky", "pinchos"}) else 7
        height = 1.9 if any(keyword in text for keyword in {"big head", "cabeza grande"}) else 1.8
        include_metal = any(keyword in text for keyword in {"punk", "metal", "chain", "cadena"})
        add_piercings = any(keyword in text for keyword in {"piercing", "piercings", "punk"})

        steps = [
            {"tool": "create_character_blockout", "result": self._call_backend("create_character_blockout", {"height": height, "collection_name": "MCP_Generated_Character"})},
            {"tool": "build_character_hair", "result": self._call_backend("build_character_hair", {"spike_count": spike_count, "collection_name": "MCP_Generated_Character_Details"})},
            {"tool": "build_character_face", "result": self._call_backend("build_character_face", {"add_piercings": add_piercings, "collection_name": "MCP_Generated_Character_Details"})},
            {"tool": "apply_character_materials", "result": self._call_backend("apply_character_materials", {"include_metal": include_metal})},
        ]

        if any(keyword in text for keyword in {"thin limbs", "thin arms", "thin legs", "extremidades finas", "brazos delgados", "piernas delgadas"}):
            steps.append(
                {
                    "tool": "apply_character_proportion_fixes",
                    "result": self._call_backend(
                        "apply_character_proportion_fixes",
                        {"deltas": {"arm_thickness": -0.18, "leg_thickness": -0.15}, "strength": 0.7},
                    ),
                }
            )

        limitations = ["This builds a stylized procedural character blockout; it does not perform automatic image-to-3D reconstruction."]
        if reference_mode:
            limitations.append(f"reference_mode='{reference_mode}' is advisory only in the current implementation.")

        return {
            "workflow": "build_character_from_description",
            "description": description,
            "style": style,
            "limitations": limitations,
            "steps": steps,
        }

    def _create_character_from_references(self, params: dict[str, Any]):
        reference_paths = self._resolve_reference_inputs(params)
        steps = [
            {"tool": "load_character_references", "result": self._call_backend("load_character_references", reference_paths)},
            {
                "tool": "create_character_blockout",
                "result": self._call_backend(
                    "create_character_blockout",
                    {"height": params.get("height", 1.9), "collection_name": params.get("blockout_collection_name")},
                ),
            },
            {
                "tool": "build_character_hair",
                "result": self._call_backend(
                    "build_character_hair",
                    {"spike_count": params.get("spike_count", 11), "collection_name": params.get("detail_collection_name")},
                ),
            },
            {
                "tool": "build_character_face",
                "result": self._call_backend(
                    "build_character_face",
                    {"add_piercings": params.get("add_piercings", True), "collection_name": params.get("detail_collection_name")},
                ),
            },
            {"tool": "apply_character_materials", "result": self._call_backend("apply_character_materials", {"include_metal": params.get("include_metal", True)})},
        ]
        return {
            "workflow": "create_character_from_references",
            "limitations": ["This is a stylized reference-guided Blender workflow. It does not perform automatic image-to-3D reconstruction."],
            "steps": steps,
        }

    def _review_and_fix_character(self, params: dict[str, Any]):
        strength = float(params.get("strength", 0.35))
        steps = [
            {"tool": "capture_character_review", "result": self._call_backend("capture_character_review", {})},
            {"tool": "compare_character_with_references", "result": self._call_backend("compare_character_with_references", {})},
            {"tool": "apply_character_proportion_fixes", "result": self._call_backend("apply_character_proportion_fixes", {"strength": strength})},
        ]
        return {"workflow": "review_and_fix_character", "steps": steps}

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

    def _limitation(self, code: str, message: str, suggestions: list[str] | None = None):
        payload = {
            "error": code,
            "message": message,
            "suggestions": suggestions or [],
        }
        LOGGER.warning("limitation %s", json.dumps(payload, ensure_ascii=False))
        return payload


def route_prompt(prompt: str) -> dict:
    return BlenderMCPAdapter().route_prompt(prompt)
