def _spec(
    command,
    *,
    public_name=None,
    description,
    params=None,
    required=None,
    layer="primitive",
    category="scene",
    expose_mcp=True,
):
    return {
        "command": command,
        "name": public_name or command,
        "description": description,
        "params": dict(params or {}),
        "required": set(required or set()),
        "layer": layer,
        "category": category,
        "expose_mcp": expose_mcp,
    }


BACKEND_TOOL_SPECS = [
    _spec(
        "get_scene_info",
        public_name="scene_info",
        description="Summarize the current Blender scene, including object count and a short object preview.",
        category="scene",
    ),
    _spec(
        "get_object_info",
        public_name="object_info",
        description="Inspect a Blender object by name, including transforms, visibility, materials, and mesh statistics.",
        params={"name": str},
        required={"name"},
        category="scene",
    ),
    _spec(
        "get_viewport_screenshot",
        public_name="viewport_screenshot",
        description="Capture a screenshot of the current Blender 3D viewport.",
        params={"filepath": str, "format": str, "max_size": int},
        category="scene",
    ),
    _spec(
        "get_telemetry_consent",
        public_name="telemetry_consent",
        description="Read whether telemetry collection is enabled in the Blender add-on preferences.",
        category="scene",
    ),
    _spec(
        "get_integration_status",
        public_name="integration_status",
        description="Check whether provider integrations are enabled and ready, optionally filtering by provider.",
        params={"provider": str},
        category="integrations",
    ),
    _spec(
        "create_primitive",
        description="Create a safe primitive mesh such as a cube, sphere, cylinder, cone, or plane in Blender.",
        params={
            "primitive_type": str,
            "name": str,
            "collection_name": str,
            "location": list,
            "rotation": list,
            "scale": list,
        },
        required={"primitive_type"},
        category="scene",
    ),
    _spec(
        "move_object",
        description="Move an existing Blender object to a target location.",
        params={"name": str, "location": list},
        required={"name", "location"},
        category="scene",
    ),
    _spec(
        "rotate_object",
        description="Rotate an existing Blender object using Euler angles in radians.",
        params={"name": str, "rotation": list},
        required={"name", "rotation"},
        category="scene",
    ),
    _spec(
        "scale_object",
        description="Scale an existing Blender object along X, Y, and Z.",
        params={"name": str, "scale": list},
        required={"name", "scale"},
        category="scene",
    ),
    _spec(
        "apply_material",
        description="Apply a simple Principled material to a mesh object using safe color and roughness inputs.",
        params={
            "object_name": str,
            "material_name": str,
            "base_color": list,
            "metallic": float,
            "roughness": float,
        },
        required={"object_name"},
        category="scene",
    ),
    _spec(
        "create_light",
        description="Create a Blender light with controlled type, color, energy, and transform.",
        params={
            "light_type": str,
            "name": str,
            "location": list,
            "rotation": list,
            "energy": float,
            "color": list,
        },
        category="scene",
    ),
    _spec(
        "set_camera",
        description="Create or update a Blender camera and optionally make it the active scene camera.",
        params={
            "name": str,
            "location": list,
            "rotation": list,
            "lens": float,
            "make_active": bool,
        },
        category="scene",
    ),
    _spec(
        "get_polyhaven_status",
        description="Check whether the Poly Haven integration is enabled and ready.",
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "get_hyper3d_status",
        description="Check whether the Hyper3D or Rodin integration is enabled and ready.",
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "get_sketchfab_status",
        description="Check whether the Sketchfab integration is enabled and ready.",
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "get_hunyuan3d_status",
        description="Check whether the Hunyuan3D integration is enabled and ready.",
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "get_polyhaven_categories",
        public_name="polyhaven_categories",
        description="List available Poly Haven categories for HDRIs, textures, models, or all assets.",
        params={"asset_type": str},
        required={"asset_type"},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "search_polyhaven_assets",
        description="Search Poly Haven assets by type and category.",
        params={"asset_type": str, "categories": str},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "download_polyhaven_asset",
        description="Download and import a Poly Haven asset into Blender when the integration is enabled.",
        params={"asset_id": str, "asset_type": str, "resolution": str, "file_format": str},
        required={"asset_id", "asset_type"},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "set_texture",
        public_name="apply_texture_set",
        description="Apply an imported texture set to an existing Blender object.",
        params={"object_name": str, "texture_id": str},
        required={"object_name", "texture_id"},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "create_rodin_job",
        description="Start a Hyper3D or Rodin generation job from text or image inputs.",
        params={"text_prompt": str, "images": list, "bbox_condition": dict},
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "poll_rodin_job_status",
        description="Poll an existing Hyper3D or Rodin generation job.",
        params={"subscription_key": str, "request_id": str},
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "import_generated_asset",
        description="Import a generated Hyper3D or Rodin asset into Blender.",
        params={"task_uuid": str, "request_id": str, "name": str},
        required={"name"},
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "search_sketchfab_models",
        description="Search 3D models on Sketchfab using text and optional category filters.",
        params={"query": str, "categories": str, "count": int, "downloadable": bool},
        required={"query"},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "get_sketchfab_model_preview",
        description="Fetch preview information for a Sketchfab model.",
        params={"uid": str},
        required={"uid"},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "download_sketchfab_model",
        description="Download and import a Sketchfab 3D model into Blender.",
        params={"uid": str, "normalize_size": bool, "target_size": float},
        required={"uid"},
        category="assets",
        expose_mcp=False,
    ),
    _spec(
        "create_hunyuan_job",
        description="Start a Hunyuan3D generation workflow from text or image input.",
        params={"text_prompt": str, "image": str},
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "poll_hunyuan_job_status",
        description="Poll an existing Hunyuan3D generation job.",
        params={"job_id": str},
        required={"job_id"},
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "import_generated_asset_hunyuan",
        description="Download and import a generated Hunyuan3D asset into Blender.",
        params={"name": str, "zip_file_url": str},
        required={"name", "zip_file_url"},
        category="integrations",
        expose_mcp=False,
    ),
    _spec(
        "load_character_references",
        description="Load front, side, and optional back character reference sheets from safe local paths.",
        params={"mode": str, "front": str, "side": str, "back": str},
        required={"front", "side"},
        category="character",
    ),
    _spec(
        "clear_character_references",
        description="Remove loaded character references from the Blender scene.",
        params={"mode": str},
        category="character",
    ),
    _spec(
        "create_character_blockout",
        description="Create a stylized character blockout mesh from parametric inputs.",
        params={"mode": str, "height": float, "collection_name": str},
        category="character",
    ),
    _spec(
        "apply_character_symmetry",
        description="Apply mirror symmetry to the current character meshes.",
        params={"mode": str, "object_names": list, "use_bisect": bool, "use_clip": bool},
        category="character",
    ),
    _spec(
        "build_character_hair",
        description="Build stylized character hair suitable for cartoon or punk-inspired looks.",
        params={"mode": str, "spike_count": int, "collection_name": str},
        category="character",
    ),
    _spec(
        "build_character_face",
        description="Build stylized face details for the current character.",
        params={"mode": str, "add_piercings": bool, "collection_name": str},
        category="character",
    ),
    _spec(
        "apply_character_materials",
        description="Apply stylized character materials such as skin, clothes, and accents.",
        params={"mode": str, "include_metal": bool},
        category="character",
    ),
    _spec(
        "capture_character_review",
        description="Capture front and side review images for the current character.",
        params={"mode": str},
        category="character",
    ),
    _spec(
        "compare_character_with_references",
        description="Compare the current character silhouette against loaded references.",
        params={"mode": str},
        category="character",
    ),
    _spec(
        "apply_character_proportion_fixes",
        description="Adjust character proportions using a comparison report or explicit deltas.",
        params={"mode": str, "correction_report": dict, "deltas": dict, "strength": float},
        category="character",
    ),
    _spec(
        "create_prop_blockout",
        description="Create parametric props in Blender such as a chair, table, crate, weapon, or simple plane.",
        params={"mode": str, "prop_type": str, "collection_name": str},
        required={"mode", "prop_type"},
        category="props",
    ),
    _spec(
        "apply_prop_symmetry",
        description="Apply mirror symmetry to current prop meshes.",
        params={"mode": str, "object_names": list, "use_bisect": bool, "use_clip": bool},
        required={"mode"},
        category="props",
    ),
    _spec(
        "apply_prop_materials",
        description="Apply simple materials to prop blockouts.",
        params={"mode": str, "include_metal": bool},
        required={"mode"},
        category="props",
    ),
    _spec(
        "create_environment_layout",
        description="Create a parametric room, corridor, shop, or kiosk layout inside Blender.",
        params={"mode": str, "layout_type": str, "collection_name": str},
        required={"mode", "layout_type"},
        category="environment",
    ),
    _spec(
        "apply_environment_materials",
        description="Apply simple materials to the current environment layout.",
        params={"mode": str},
        required={"mode"},
        category="environment",
    ),
]


def _python_type_to_schema(expected_type):
    mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    return dict(mapping.get(expected_type, {"type": "string"}))


def build_input_schema(spec):
    properties = {}
    for param_name, param_type in spec["params"].items():
        properties[param_name] = _python_type_to_schema(param_type)

    schema = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    required = sorted(spec["required"])
    if required:
        schema["required"] = required
    return schema


def iter_backend_tools(*, exposed_only=False):
    for spec in BACKEND_TOOL_SPECS:
        if exposed_only and not spec["expose_mcp"]:
            continue
        yield spec


def get_backend_tool(identifier):
    for spec in BACKEND_TOOL_SPECS:
        if identifier in {spec["command"], spec["name"]}:
            return spec
    return None


def build_mcp_tool_definition(spec):
    return {
        "name": spec["name"],
        "description": spec["description"],
        "inputSchema": build_input_schema(spec),
    }


COMMAND_SCHEMAS = {
    spec["command"]: {
        "params": dict(spec["params"]),
        "required": set(spec["required"]),
    }
    for spec in BACKEND_TOOL_SPECS
}
