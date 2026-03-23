import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blender_mcp_pro.tool_registry import build_input_schema, iter_backend_tools


def _tool(
    name,
    *,
    description,
    input_schema,
    layer,
    domain,
    availability,
    backend_command=None,
    provider_gated=False,
):
    return {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "layer": layer,
        "domain": domain,
        "availability": availability,
        "backend_command": backend_command,
        "provider_gated": provider_gated,
    }


BACKEND_EXPOSED_TOOLS = [
    _tool(
        spec["name"],
        description=spec["description"],
        input_schema=build_input_schema(spec),
        layer="primitive",
        domain=spec["category"],
        availability="server",
        backend_command=spec["command"],
        provider_gated=spec["category"] in {"assets", "integrations"},
    )
    for spec in iter_backend_tools(exposed_only=True)
]


CLIENT_TOOLS = [
    _tool(
        "search_assets",
        description="Search supported asset providers using a small, provider-aware primitive surface.",
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string", "enum": ["polyhaven", "sketchfab"]},
                "query": {"type": "string"},
                "asset_type": {"type": "string", "enum": ["hdris", "textures", "models", "all"]},
                "categories": {"type": "string"},
                "count": {"type": "integer"},
                "downloadable": {"type": "boolean"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
        layer="primitive",
        domain="assets",
        availability="workflow",
        provider_gated=True,
    ),
    _tool(
        "import_asset",
        description="Import a supported asset through existing safe integrations such as Poly Haven or Sketchfab.",
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string", "enum": ["polyhaven", "sketchfab"]},
                "asset_id": {"type": "string"},
                "asset_type": {"type": "string"},
                "uid": {"type": "string"},
                "resolution": {"type": "string"},
                "file_format": {"type": "string"},
                "normalize_size": {"type": "boolean"},
                "target_size": {"type": "number"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
        layer="primitive",
        domain="assets",
        availability="workflow",
        provider_gated=True,
    ),
    _tool(
        "generate_scene_plan",
        description="Generate a structured scene plan from a natural-language description using only real safe primitives.",
        input_schema={
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "style": {"type": "string"},
                "use_assets": {"type": "boolean"},
            },
            "required": ["description"],
            "additionalProperties": False,
        },
        layer="generative",
        domain="generative",
        availability="workflow",
    ),
    _tool(
        "apply_scene_plan",
        description="Apply a previously generated scene plan using safe primitives and blockout tools.",
        input_schema={
            "type": "object",
            "properties": {"plan": {"type": "object"}},
            "required": ["plan"],
            "additionalProperties": False,
        },
        layer="generative",
        domain="generative",
        availability="workflow",
    ),
    _tool(
        "build_scene_from_description",
        description="Build a simple scene from natural language by generating and applying a safe scene plan.",
        input_schema={
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "style": {"type": "string"},
                "use_assets": {"type": "boolean"},
            },
            "required": ["description"],
            "additionalProperties": False,
        },
        layer="generative",
        domain="generative",
        availability="workflow",
    ),
    _tool(
        "build_character_from_description",
        description="Build a stylized character blockout from natural language using the real character primitives.",
        input_schema={
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "style": {"type": "string"},
                "reference_mode": {"type": "string"},
            },
            "required": ["description"],
            "additionalProperties": False,
        },
        layer="generative",
        domain="generative",
        availability="workflow",
    ),
    _tool(
        "create_character_from_references",
        description="Build a stylized character from safe local reference sheets using the real character primitives.",
        input_schema={
            "type": "object",
            "properties": {
                "reference_dir": {"type": "string"},
                "front": {"type": "string"},
                "side": {"type": "string"},
                "back": {"type": "string"},
                "height": {"type": "number"},
                "blockout_collection_name": {"type": "string"},
                "detail_collection_name": {"type": "string"},
                "spike_count": {"type": "integer"},
                "add_piercings": {"type": "boolean"},
                "include_metal": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        layer="generative",
        domain="generative",
        availability="workflow",
    ),
    _tool(
        "review_and_fix_character",
        description="Capture character review screenshots, compare against references, and apply a safe fix pass.",
        input_schema={
            "type": "object",
            "properties": {"strength": {"type": "number"}},
            "additionalProperties": False,
        },
        layer="generative",
        domain="generative",
        availability="workflow",
    ),
]


TOOLS = BACKEND_EXPOSED_TOOLS + CLIENT_TOOLS
TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
CALLABLE_TOOLS = list(TOOLS)
CALLABLE_TOOL_NAMES = {tool["name"] for tool in CALLABLE_TOOLS}
SERVER_TOOL_NAMES = {tool["name"] for tool in TOOLS if tool["availability"] == "server"}
WORKFLOW_TOOL_NAMES = {tool["name"] for tool in TOOLS if tool["availability"] == "workflow"}
PRIMITIVE_TOOL_NAMES = {tool["name"] for tool in TOOLS if tool["layer"] == "primitive"}
GENERATIVE_TOOL_NAMES = {tool["name"] for tool in TOOLS if tool["layer"] == "generative"}
