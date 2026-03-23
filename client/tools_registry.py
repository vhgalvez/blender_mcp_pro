TOOLS = [
    {
        "name": "get_scene_info",
        "description": "Get current Blender scene info.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_object_info",
        "description": "Get transform and mesh info for a Blender object by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "load_character_references",
        "description": "Load front and side reference images for a stylized character workflow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "front": {"type": "string"},
                "side": {"type": "string"},
                "back": {"type": "string"},
            },
            "required": ["front", "side"],
        },
    },
    {
        "name": "clear_character_references",
        "description": "Clear loaded character reference images from the scene.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_character_blockout",
        "description": "Create a stylized character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "height": {"type": "number"},
                "collection_name": {"type": "string"},
            },
        },
    },
    {
        "name": "apply_character_symmetry",
        "description": "Apply mirror symmetry to the current character meshes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_names": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "use_bisect": {"type": "boolean"},
                "use_clip": {"type": "boolean"},
            },
        },
    },
    {
        "name": "build_character_hair",
        "description": "Build stylized hair for the active character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spike_count": {"type": "integer"},
                "collection_name": {"type": "string"},
            },
        },
    },
    {
        "name": "build_character_face",
        "description": "Build stylized face details for the active character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "add_piercings": {"type": "boolean"},
                "collection_name": {"type": "string"},
            },
        },
    },
    {
        "name": "apply_character_materials",
        "description": "Apply basic materials to the active character.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_metal": {"type": "boolean"},
            },
        },
    },
    {
        "name": "capture_character_review",
        "description": "Capture front and side review screenshots of the current character.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "compare_character_with_references",
        "description": "Compare the current character with loaded references using heuristic proportions.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "apply_character_proportion_fixes",
        "description": "Apply character proportion fixes from heuristics or explicit deltas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "correction_report": {"type": "object"},
                "deltas": {"type": "object"},
                "strength": {"type": "number"},
            },
        },
    },
    {
        "name": "create_prop_blockout",
        "description": "Create a basic prop blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prop_type": {"type": "string"},
                "collection_name": {"type": "string"},
            },
            "required": ["prop_type"],
        },
    },
    {
        "name": "apply_prop_materials",
        "description": "Apply simple materials to the current prop blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_metal": {"type": "boolean"},
            },
        },
    },
    {
        "name": "create_environment_layout",
        "description": "Create a basic environment layout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "layout_type": {"type": "string"},
                "collection_name": {"type": "string"},
            },
            "required": ["layout_type"],
        },
    },
    {
        "name": "apply_environment_materials",
        "description": "Apply simple materials to the current environment layout.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_polyhaven_status",
        "description": "Get Poly Haven integration status from Blender.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_polyhaven_assets",
        "description": "Search Poly Haven assets through the Blender backend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_type": {"type": "string"},
                "categories": {"type": "string"},
            },
        },
    },
    {
        "name": "download_polyhaven_asset",
        "description": "Download and import a Poly Haven asset through Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "asset_type": {"type": "string"},
                "resolution": {"type": "string"},
                "file_format": {"type": "string"},
            },
            "required": ["asset_id", "asset_type"],
        },
    },
    {
        "name": "set_texture",
        "description": "Apply a loaded texture set to an object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"},
                "texture_id": {"type": "string"},
            },
            "required": ["object_name", "texture_id"],
        },
    },
]
