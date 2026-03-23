TOOLS = [
    {
        "name": "get_scene_info",
        "domain": "scene",
        "availability": "server",
        "description": "Get a compact summary of the current Blender scene. Obtiene un resumen compacto de la escena actual.",
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
        "description": "Get transform, visibility, materials, and mesh stats for a Blender object by name. Obtiene transformaciones, materiales y estadisticas de malla por nombre.",
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
        "description": "Capture a screenshot of the current 3D viewport. Captura una imagen del viewport 3D actual.",
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
        "description": "Read the telemetry consent flag from Blender add-on preferences. Lee el consentimiento de telemetria del add-on.",
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
        "description": "Load front and side reference sheets, with optional back sheet, from safe local input paths. Carga referencias frontales, laterales y opcionalmente traseras.",
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
        "description": "Remove loaded character references from the scene. Elimina las referencias de personaje cargadas en la escena.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "create_character_blockout",
        "domain": "character",
        "availability": "server",
        "description": "Create a stylized cartoon character blockout. Crea un blockout de personaje caricaturesco y estilizado.",
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
        "description": "Apply mirror symmetry to current character meshes. Aplica simetria espejo a las mallas del personaje.",
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
        "description": "Build stylized punk-like hair for the current character blockout. Construye pelo estilizado tipo punk para el personaje actual.",
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
        "description": "Build stylized face details for the current character blockout. Construye detalles faciales estilizados para el personaje.",
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
        "description": "Apply the built-in stylized character materials. Aplica materiales estilizados integrados al personaje.",
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
        "description": "Capture front and side review screenshots for the current character. Captura vistas de revision frontal y lateral del personaje.",
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
        "description": "Compare the current character with loaded references using silhouette heuristics. Compara el personaje actual con las referencias usando heuristicas.",
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
        "description": "Apply proportional fixes to the active character using a comparison report or explicit deltas. Aplica correcciones de proporcion al personaje activo.",
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
        "name": "create_prop_blockout",
        "domain": "props",
        "availability": "server",
        "description": "Create a stylized prop blockout such as a chair, table, crate, or weapon. Crea un blockout de prop como silla, mesa, caja o arma.",
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
        "description": "Apply mirror symmetry to current prop meshes. Aplica simetria espejo a props actuales.",
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
        "description": "Apply simple materials to the current prop blockout. Aplica materiales simples al prop actual.",
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
        "description": "Create an environment layout such as a room, corridor, shop, or kiosk. Crea un layout de entorno como habitacion, pasillo, tienda o kiosco.",
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
        "description": "Apply simple materials to the active environment layout. Aplica materiales simples al entorno activo.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_polyhaven_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Get the Poly Haven integration status from Blender settings. Obtiene el estado de integracion de Poly Haven.",
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
        "description": "Get the Hyper3D or Rodin integration status from Blender settings. Obtiene el estado de Hyper3D o Rodin.",
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
        "description": "Get the Sketchfab integration status from Blender settings. Obtiene el estado de integracion de Sketchfab.",
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
        "description": "Get the Hunyuan3D integration status from Blender settings. Obtiene el estado de Hunyuan3D.",
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
        "description": "Get Poly Haven categories for hdris, textures, models, or all. Obtiene categorias de Poly Haven.",
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
        "description": "Search Poly Haven assets through the Blender backend integration. Busca assets en Poly Haven desde Blender.",
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
        "description": "Download and import a Poly Haven asset through Blender. Descarga e importa un asset de Poly Haven.",
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
        "description": "Apply a previously imported texture set to a Blender object. Aplica una textura importada a un objeto de Blender.",
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
        "description": "Create a Hyper3D or Rodin generation job. Crea un trabajo de generacion Hyper3D o Rodin.",
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
        "description": "Poll a Hyper3D or Rodin generation job. Consulta el estado de un trabajo de Hyper3D o Rodin.",
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
        "description": "Import a generated Hyper3D or Rodin asset into Blender. Importa un asset generado por Hyper3D o Rodin.",
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
        "description": "Search Sketchfab models through the Blender backend. Busca modelos de Sketchfab desde Blender.",
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
        "description": "Get preview information for a Sketchfab model UID. Obtiene informacion previa de un modelo de Sketchfab.",
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
        "description": "Download and import a Sketchfab model into Blender. Descarga e importa un modelo de Sketchfab.",
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
        "description": "Create a Hunyuan3D generation job. Crea un trabajo de generacion Hunyuan3D.",
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
        "description": "Poll a Hunyuan3D official API generation job. Consulta el estado de un trabajo de Hunyuan3D.",
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
        "description": "Download and import a generated Hunyuan asset from a ZIP URL. Descarga e importa un asset generado por Hunyuan.",
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
        "name": "create_street_blockout",
        "domain": "environment",
        "availability": "unavailable",
        "description": "Planned future helper. The current Blender server does not implement a real street blockout tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection_name": {"type": "string", "description": "Optional destination collection name."},
            },
            "additionalProperties": False,
        },
    },
]

TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
CALLABLE_TOOLS = [tool for tool in TOOLS if tool["availability"] == "server"]
CALLABLE_TOOL_NAMES = {tool["name"] for tool in CALLABLE_TOOLS}
UNAVAILABLE_TOOLS = [tool for tool in TOOLS if tool["availability"] == "unavailable"]
UNAVAILABLE_TOOL_NAMES = {tool["name"] for tool in UNAVAILABLE_TOOLS}
