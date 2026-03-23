TOOLS = [
    {
        "name": "get_scene_info",
        "domain": "scene",
        "availability": "server",
        "description": "Get a compact summary of the current Blender scene.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_object_info",
        "domain": "scene",
        "availability": "server",
        "description": "Get transform, visibility, materials, and mesh stats for a Blender object by name.",
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
        "name": "get_viewport_screenshot",
        "domain": "scene",
        "availability": "server",
        "description": "Capture a screenshot of the current 3D viewport.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Optional screenshot output path inside the safe screenshot area.",
                },
                "format": {
                    "type": "string",
                    "enum": ["png", "jpg", "jpeg"],
                    "description": "Image format.",
                },
                "max_size": {
                    "type": "integer",
                    "description": "Maximum width or height after optional resize.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_telemetry_consent",
        "domain": "scene",
        "availability": "server",
        "description": "Read the current telemetry consent flag from Blender add-on preferences.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "list_collections",
        "domain": "scene",
        "availability": "unavailable",
        "description": "Planned future helper. The current Blender server does not implement collection listing as a command.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "load_character_references",
        "domain": "character",
        "availability": "server",
        "description": "Load front and side reference sheets, with optional back sheet, from safe local input paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "front": {"type": "string", "description": "Safe local path to the front reference image."},
                "side": {"type": "string", "description": "Safe local path to the side or profile reference image."},
                "back": {"type": "string", "description": "Optional safe local path to the back reference image."},
            },
            "required": ["front", "side"],
            "additionalProperties": False,
        },
    },
    {
        "name": "clear_character_references",
        "domain": "character",
        "availability": "server",
        "description": "Remove loaded character references from the scene.",
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
        "description": "Adapter workflow that chains reference loading, blockout, hair, face, and materials using real server commands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reference_dir": {"type": "string", "description": "Directory containing front/back/profile sheets."},
                "front": {"type": "string", "description": "Optional explicit front image path."},
                "side": {"type": "string", "description": "Optional explicit side/profile image path."},
                "back": {"type": "string", "description": "Optional explicit back image path."},
                "height": {"type": "number", "description": "Target character height."},
                "blockout_collection_name": {"type": "string", "description": "Optional collection for the blockout."},
                "detail_collection_name": {"type": "string", "description": "Optional collection for face and hair details."},
                "spike_count": {"type": "integer", "description": "Optional stylized hair spike count."},
                "add_piercings": {"type": "boolean", "description": "Whether to add stylized piercings."},
                "include_metal": {"type": "boolean", "description": "Whether to include metallic accents."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_character_blockout",
        "domain": "character",
        "availability": "server",
        "description": "Create a stylized cartoon character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "height": {"type": "number", "description": "Target character height in Blender units."},
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_character_symmetry",
        "domain": "character",
        "availability": "server",
        "description": "Apply mirror symmetry to current character meshes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of object names to target.",
                },
                "use_bisect": {"type": "boolean", "description": "Whether to bisect on the mirror axis."},
                "use_clip": {"type": "boolean", "description": "Whether to enable mirror clipping."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "build_character_hair",
        "domain": "character",
        "availability": "server",
        "description": "Build stylized punk-like hair for the current character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spike_count": {"type": "integer", "description": "Number of stylized hair spikes."},
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "build_character_face",
        "domain": "character",
        "availability": "server",
        "description": "Build stylized face details for the current character blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "add_piercings": {"type": "boolean", "description": "Whether to add stylized piercings."},
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_character_materials",
        "domain": "character",
        "availability": "server",
        "description": "Apply the built-in stylized character materials.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_metal": {"type": "boolean", "description": "Whether to include metallic accents."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "capture_character_review",
        "domain": "character",
        "availability": "server",
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
        "availability": "server",
        "description": "Compare the current stylized character with loaded references using silhouette heuristics.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_character_proportion_fixes",
        "domain": "character",
        "availability": "server",
        "description": "Apply proportional fixes to the active character using a comparison report or explicit deltas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "correction_report": {"type": "object", "description": "Optional comparison report."},
                "deltas": {"type": "object", "description": "Optional explicit proportional delta overrides."},
                "strength": {"type": "number", "description": "Fix strength from 0.0 to 1.0."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "review_and_fix_character",
        "domain": "character",
        "availability": "adapter_workflow",
        "description": "Adapter workflow that captures review screenshots, compares the character to references, and applies a basic fix pass.",
        "input_schema": {
            "type": "object",
            "properties": {
                "strength": {"type": "number", "description": "Fix strength from 0.0 to 1.0."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_prop_blockout",
        "domain": "props",
        "availability": "server",
        "description": "Create a stylized prop blockout such as a chair, table, crate, or weapon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prop_type": {
                    "type": "string",
                    "enum": ["chair", "table", "crate", "weapon"],
                    "description": "Supported prop archetype.",
                },
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "required": ["prop_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_prop_symmetry",
        "domain": "props",
        "availability": "server",
        "description": "Apply mirror symmetry to current prop meshes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of prop object names.",
                },
                "use_bisect": {"type": "boolean", "description": "Whether to bisect on the mirror axis."},
                "use_clip": {"type": "boolean", "description": "Whether to enable mirror clipping."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_prop_materials",
        "domain": "props",
        "availability": "server",
        "description": "Apply simple materials to the current prop blockout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_metal": {"type": "boolean", "description": "Whether metallic materials should be included."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_environment_layout",
        "domain": "environment",
        "availability": "server",
        "description": "Create an environment layout such as a room, corridor, shop, or kiosk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "layout_type": {
                    "type": "string",
                    "enum": ["room", "corridor", "shop", "kiosk"],
                    "description": "Supported layout archetype.",
                },
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "required": ["layout_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_environment_materials",
        "domain": "environment",
        "availability": "server",
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
        "description": "Adapter workflow that creates a shop layout and applies environment materials using real server commands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_room_blockout",
        "domain": "environment",
        "availability": "adapter_alias",
        "description": "Adapter alias that maps to the real server tool create_environment_layout with layout_type='room'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_street_blockout",
        "domain": "environment",
        "availability": "unavailable",
        "description": "Planned future helper. The current server does not implement a real street blockout tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_polyhaven_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Get the Poly Haven integration status from Blender add-on settings.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_hyper3d_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Get the Hyper3D / Rodin integration status from Blender add-on settings.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_sketchfab_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Get the Sketchfab integration status from Blender add-on settings.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_hunyuan3d_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Get the Hunyuan3D integration status from Blender add-on settings.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_polyhaven_categories",
        "domain": "integrations",
        "availability": "server",
        "description": "Get Poly Haven categories for hdris, textures, models, or all.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "enum": ["hdris", "textures", "models", "all"],
                    "description": "Poly Haven asset type scope.",
                }
            },
            "required": ["asset_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_polyhaven_assets",
        "domain": "integrations",
        "availability": "server",
        "description": "Search Poly Haven assets through the current Blender backend integration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "enum": ["hdris", "textures", "models", "all"],
                    "description": "Optional asset type filter.",
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
        "domain": "integrations",
        "availability": "server",
        "description": "Download and import a Poly Haven asset through Blender. Requires Poly Haven to be enabled in add-on settings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string", "description": "Poly Haven asset identifier."},
                "asset_type": {"type": "string", "description": "Poly Haven asset type."},
                "resolution": {"type": "string", "description": "Optional resolution such as 1k, 2k, or 4k."},
                "file_format": {"type": "string", "description": "Optional backend-supported file format hint."},
            },
            "required": ["asset_id", "asset_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_texture",
        "domain": "integrations",
        "availability": "server",
        "description": "Apply a previously imported texture set to a Blender object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "description": "Target Blender object name."},
                "texture_id": {"type": "string", "description": "Previously imported texture identifier."},
            },
            "required": ["object_name", "texture_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_rodin_job",
        "domain": "integrations",
        "availability": "server",
        "description": "Create a Hyper3D / Rodin generation job. Requires Hyper3D to be enabled and configured.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text_prompt": {"type": "string"},
                "images": {"type": "array", "items": {"type": "string"}},
                "bbox_condition": {"type": "object"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "poll_rodin_job_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Poll a Hyper3D / Rodin generation job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subscription_key": {"type": "string"},
                "request_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "import_generated_asset",
        "domain": "integrations",
        "availability": "server",
        "description": "Import a generated Hyper3D / Rodin asset into Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to assign to the imported asset."},
                "task_uuid": {"type": "string"},
                "request_id": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_sketchfab_models",
        "domain": "integrations",
        "availability": "server",
        "description": "Search Sketchfab models through the Blender backend. Requires Sketchfab to be enabled and configured.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "categories": {"type": "string"},
                "count": {"type": "integer"},
                "downloadable": {"type": "boolean"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_sketchfab_model_preview",
        "domain": "integrations",
        "availability": "server",
        "description": "Get preview information for a Sketchfab model UID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "uid": {"type": "string"},
            },
            "required": ["uid"],
            "additionalProperties": False,
        },
    },
    {
        "name": "download_sketchfab_model",
        "domain": "integrations",
        "availability": "server",
        "description": "Download and import a Sketchfab model into Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "uid": {"type": "string"},
                "normalize_size": {"type": "boolean"},
                "target_size": {"type": "number"},
            },
            "required": ["uid"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_hunyuan_job",
        "domain": "integrations",
        "availability": "server",
        "description": "Create a Hunyuan3D generation job. Requires Hunyuan3D to be enabled in Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text_prompt": {"type": "string"},
                "image": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "poll_hunyuan_job_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Poll a Hunyuan3D official API generation job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "import_generated_asset_hunyuan",
        "domain": "integrations",
        "availability": "server",
        "description": "Download and import a generated Hunyuan asset from a ZIP URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "zip_file_url": {"type": "string"},
            },
            "required": ["name", "zip_file_url"],
            "additionalProperties": False,
        },
    },
]
