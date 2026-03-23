from .protocol import COMMAND_SCHEMAS


MCP_NAME_OVERRIDES = {
    "get_scene_info": "scene_info",
    "search_sketchfab_models": "search_3d_models",
    "download_sketchfab_model": "download_3d_model",
}


TOOL_DESCRIPTIONS = {
    "get_scene_info": "Get information about the current Blender scene, including object count and a short object preview.",
    "get_object_info": "Inspect a Blender object by name, including transforms, visibility, materials, and mesh statistics.",
    "get_viewport_screenshot": "Capture a screenshot of the current Blender 3D viewport.",
    "get_telemetry_consent": "Read whether telemetry collection is enabled in the Blender add-on preferences.",
    "create_primitive": "Create a safe primitive mesh such as a cube, sphere, cylinder, cone, or plane in Blender.",
    "move_object": "Move an existing Blender object to a target location.",
    "rotate_object": "Rotate an existing Blender object using Euler angles in radians.",
    "scale_object": "Scale an existing Blender object along X, Y, and Z.",
    "apply_material": "Apply a simple Principled material to a mesh object using safe color and roughness inputs.",
    "create_light": "Create a Blender light with controlled type, color, energy, and transform.",
    "set_camera": "Create or update a Blender camera and optionally make it the active scene camera.",
    "get_polyhaven_status": "Check whether the Poly Haven integration is enabled and ready.",
    "get_hyper3d_status": "Check whether the Hyper3D or Rodin integration is enabled and ready.",
    "get_sketchfab_status": "Check whether the Sketchfab integration is enabled and ready.",
    "get_hunyuan3d_status": "Check whether the Hunyuan3D integration is enabled and ready.",
    "get_polyhaven_categories": "List available Poly Haven categories for HDRIs, textures, models, or all assets.",
    "search_polyhaven_assets": "Search Poly Haven assets by type and category.",
    "download_polyhaven_asset": "Download and import a Poly Haven asset into Blender when the integration is enabled.",
    "set_texture": "Apply an imported texture set to an existing Blender object.",
    "create_rodin_job": "Start a Hyper3D or Rodin generation job from text or image inputs.",
    "poll_rodin_job_status": "Poll an existing Hyper3D or Rodin generation job.",
    "import_generated_asset": "Import a generated Hyper3D or Rodin asset into Blender.",
    "search_sketchfab_models": "Search 3D models on Sketchfab using text and optional category filters.",
    "get_sketchfab_model_preview": "Fetch preview information for a Sketchfab model.",
    "download_sketchfab_model": "Download and import a Sketchfab 3D model into Blender.",
    "create_hunyuan_job": "Start a Hunyuan3D generation workflow from text or image input.",
    "poll_hunyuan_job_status": "Poll an existing Hunyuan3D generation job.",
    "import_generated_asset_hunyuan": "Download and import a generated Hunyuan3D asset into Blender.",
    "load_character_references": "Load front, side, and optional back character reference sheets from safe local paths.",
    "clear_character_references": "Remove loaded character references from the Blender scene.",
    "create_character_blockout": "Create a stylized character blockout mesh from parametric inputs.",
    "apply_character_symmetry": "Apply mirror symmetry to the current character meshes.",
    "build_character_hair": "Build stylized character hair, suitable for cartoon or punk-inspired looks.",
    "build_character_face": "Build stylized face details for the current character.",
    "apply_character_materials": "Apply stylized character materials such as skin, clothes, and accents.",
    "capture_character_review": "Capture front and side review images for the current character.",
    "compare_character_with_references": "Compare the current character silhouette against loaded references.",
    "apply_character_proportion_fixes": "Adjust character proportions using a comparison report or explicit deltas.",
    "create_prop_blockout": "Create parametric props in Blender such as a chair, table, crate, or weapon.",
    "apply_prop_symmetry": "Apply mirror symmetry to current prop meshes.",
    "apply_prop_materials": "Apply simple materials to prop blockouts.",
    "create_environment_layout": "Create a parametric room, corridor, shop, or kiosk layout inside Blender.",
    "apply_environment_materials": "Apply simple materials to the current environment layout.",
}


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


def build_tool_registry(dispatcher):
    tools = []
    for command_name, schema in sorted(COMMAND_SCHEMAS.items()):
        if not hasattr(dispatcher, f"cmd_{command_name}"):
            continue

        properties = {}
        for param_name, param_type in schema.get("params", {}).items():
            properties[param_name] = _python_type_to_schema(param_type)

        input_schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        required = sorted(schema.get("required", set()))
        if required:
            input_schema["required"] = required

        tools.append(
            {
                "name": MCP_NAME_OVERRIDES.get(command_name, command_name),
                "command": command_name,
                "description": TOOL_DESCRIPTIONS.get(command_name, command_name.replace("_", " ")),
                "input_schema": input_schema,
            }
        )
    return tools


def resolve_tool_name(dispatcher, requested_name):
    for tool in build_tool_registry(dispatcher):
        if tool["name"] == requested_name or tool["command"] == requested_name:
            return tool
    return None
