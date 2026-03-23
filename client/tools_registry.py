TOOLS = [
    {
        "name": "get_scene_info",
        "domain": "scene",
        "availability": "implemented",
        "description": "Get a compact summary of the current Blender scene, including object count and a preview of scene objects.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_object_info",
        "domain": "scene",
        "availability": "implemented",
        "description": "Get transform and mesh details for a Blender object by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Exact Blender object name.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_collections",
        "domain": "scene",
        "availability": "placeholder",
        "description": "Placeholder for future collection listing support. The current Blender backend does not expose collections yet.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "create_character_from_references",
        "domain": "character",
        "availability": "adapter_workflow",
        "description": "Run a practical stylized character workflow from reference sheets using existing Blender backend steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reference_dir": {
                    "type": "string",
                    "description": "Directory containing front/side/back or profile reference images.",
                },
                "front": {
                    "type": "string",
                    "description": "Optional explicit front reference image path.",
                },
                "side": {
                    "type": "string",
                    "description": "Optional explicit side or profile reference image path.",
                },
                "back": {
                    "type": "string",
                    "description": "Optional explicit back reference image path.",
                },
                "height": {
                    "type": "number",
                    "description": "Target stylized character height in Blender units.",
                },
                "blockout_collection_name": {
                    "type": "string",
                    "description": "Optional collection name for the base character blockout.",
                },
                "detail_collection_name": {
                    "type": "string",
                    "description": "Optional collection name for face and hair details.",
                },
                "spike_count": {
                    "type": "integer",
                    "description": "Optional number of stylized hair spikes.",
                },
                "add_piercings": {
                    "type": "boolean",
                    "description": "Whether to add stylized face piercings.",
                },
                "include_metal": {
                    "type": "boolean",
                    "description": "Whether to include metallic accents in generated materials.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_character_blockout",
        "domain": "character",
        "availability": "implemented",
        "description": "Create a stylized cartoon character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "height": {
                    "type": "number",
                    "description": "Target character height in Blender units.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "capture_character_review",
        "domain": "character",
        "availability": "implemented",
        "description": "Capture front and side review screenshots for the current character.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_character_with_references",
        "domain": "character",
        "availability": "implemented",
        "description": "Compare the current stylized character to the loaded reference sheets using heuristic silhouette measurements.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_character_proportion_fixes",
        "domain": "character",
        "availability": "implemented",
        "description": "Apply automatic or explicit proportional fixes to the active character.",
        "input_schema": {
            "type": "object",
            "properties": {
                "correction_report": {
                    "type": "object",
                    "description": "Optional report from compare_character_with_references.",
                },
                "deltas": {
                    "type": "object",
                    "description": "Optional explicit delta overrides keyed by body region.",
                },
                "strength": {
                    "type": "number",
                    "description": "Blend factor from 0.0 to 1.0.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "review_and_fix_character",
        "domain": "character",
        "availability": "adapter_workflow",
        "description": "Capture review screenshots, compare the character to references, and apply a basic fix pass.",
        "input_schema": {
            "type": "object",
            "properties": {
                "strength": {
                    "type": "number",
                    "description": "Blend factor from 0.0 to 1.0 for the fix pass.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_prop_blockout",
        "domain": "props",
        "availability": "implemented",
        "description": "Create a stylized prop blockout such as a chair, table, crate, or weapon.",
        "input_schema": {
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
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_prop_materials",
        "domain": "props",
        "availability": "implemented",
        "description": "Apply simple materials to the active prop blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_metal": {
                    "type": "boolean",
                    "description": "Whether metallic materials should be included.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_environment_layout",
        "domain": "environment",
        "availability": "implemented",
        "description": "Create an environment layout such as a room, corridor, shop, or kiosk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "layout_type": {
                    "type": "string",
                    "enum": ["room", "corridor", "shop", "kiosk"],
                    "description": "Supported layout archetype.",
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "required": ["layout_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_environment_materials",
        "domain": "environment",
        "availability": "implemented",
        "description": "Apply simple materials to the active environment layout.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "create_shop_scene",
        "domain": "environment",
        "availability": "adapter_workflow",
        "description": "Create a compact shop or interior scene and apply environment materials.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_room_blockout",
        "domain": "environment",
        "availability": "adapter_alias",
        "description": "Create a room blockout using the existing environment layout backend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_street_blockout",
        "domain": "environment",
        "availability": "adapter_alias",
        "description": "Create a street-like blockout using the current corridor layout backend as a practical local approximation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Optional destination collection name.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "search_polyhaven_assets",
        "domain": "assets",
        "availability": "implemented",
        "description": "Search Poly Haven assets through the current Blender backend integration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "Optional asset type such as texture, hdri, or model.",
                },
                "categories": {
                    "type": "string",
                    "description": "Optional comma-separated categories filter.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "download_polyhaven_asset",
        "domain": "assets",
        "availability": "implemented",
        "description": "Download and import a Poly Haven asset through Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Poly Haven asset identifier.",
                },
                "asset_type": {
                    "type": "string",
                    "description": "Asset type such as texture, hdri, or model.",
                },
                "resolution": {
                    "type": "string",
                    "description": "Optional resolution such as 1k, 2k, or 4k.",
                },
                "file_format": {
                    "type": "string",
                    "description": "Optional backend-supported file format hint.",
                },
            },
            "required": ["asset_id", "asset_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_texture",
        "domain": "assets",
        "availability": "implemented",
        "description": "Apply a previously imported texture set to a Blender object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "Target Blender object name.",
                },
                "texture_id": {
                    "type": "string",
                    "description": "Previously imported texture identifier.",
                },
            },
            "required": ["object_name", "texture_id"],
            "additionalProperties": False,
        },
    },
]
