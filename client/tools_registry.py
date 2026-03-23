TOOLS = [
    {
        "name": "get_scene_info",
        "domain": "scene",
        "availability": "server",
        "description": "Get information about the current Blender scene, including object count and a short object preview. Obtiene informacion de la escena actual.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_object_info",
        "domain": "scene",
        "availability": "server",
        "description": "Inspect a Blender object by name, including transform, materials, and mesh statistics. Inspecciona un objeto de Blender por nombre.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Exact Blender object name."}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_viewport_screenshot",
        "domain": "scene",
        "availability": "server",
        "description": "Capture a screenshot of the current Blender viewport. Captura una imagen del viewport actual.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "format": {"type": "string", "enum": ["png", "jpg", "jpeg"]},
                "max_size": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_telemetry_consent",
        "domain": "scene",
        "availability": "server",
        "description": "Read whether telemetry collection is enabled in the Blender add-on preferences. Consulta si la telemetria esta activada.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "create_primitive",
        "domain": "primitive",
        "availability": "server",
        "description": "Create a safe primitive mesh in Blender, such as a cube, sphere, cylinder, cone, or plane. Crea una primitiva segura en Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "primitive_type": {"type": "string", "enum": ["cube", "sphere", "cylinder", "cone", "plane"]},
                "name": {"type": "string"},
                "collection_name": {"type": "string"},
                "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "scale": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            },
            "required": ["primitive_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_object",
        "domain": "primitive",
        "availability": "server",
        "description": "Move an existing Blender object to a new location. Mueve un objeto existente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            },
            "required": ["name", "location"],
            "additionalProperties": False,
        },
    },
    {
        "name": "rotate_object",
        "domain": "primitive",
        "availability": "server",
        "description": "Rotate an existing Blender object using Euler angles in radians. Rota un objeto existente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            },
            "required": ["name", "rotation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "scale_object",
        "domain": "primitive",
        "availability": "server",
        "description": "Scale an existing Blender object in X, Y, and Z. Escala un objeto existente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "scale": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            },
            "required": ["name", "scale"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_material",
        "domain": "primitive",
        "availability": "server",
        "description": "Apply a simple safe material to a Blender mesh object. Aplica un material simple y seguro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"},
                "material_name": {"type": "string"},
                "base_color": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "metallic": {"type": "number"},
                "roughness": {"type": "number"},
            },
            "required": ["object_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_light",
        "domain": "primitive",
        "availability": "server",
        "description": "Create a Blender light with controlled type, color, and energy. Crea una luz en Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "light_type": {"type": "string", "enum": ["POINT", "SUN", "SPOT", "AREA"]},
                "name": {"type": "string"},
                "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "energy": {"type": "number"},
                "color": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "set_camera",
        "domain": "primitive",
        "availability": "server",
        "description": "Create or update a camera and optionally make it active. Crea o actualiza una camara.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "lens": {"type": "number"},
                "make_active": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "create_prop_blockout",
        "domain": "props",
        "availability": "server",
        "description": "Create a simple prop such as a chair, table, crate, weapon, or small plane in Blender. Crea un prop simple en Blender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prop_type": {"type": "string", "enum": ["chair", "table", "crate", "weapon", "plane"]},
                "collection_name": {"type": "string"},
            },
            "required": ["prop_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_prop_symmetry",
        "domain": "props",
        "availability": "server",
        "description": "Apply mirror symmetry to the current prop blockout meshes. Aplica simetria a props actuales.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_names": {"type": "array", "items": {"type": "string"}},
                "use_bisect": {"type": "boolean"},
                "use_clip": {"type": "boolean"},
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
            "properties": {"include_metal": {"type": "boolean"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "create_environment_layout",
        "domain": "environment",
        "availability": "server",
        "description": "Create a parametric room, corridor, shop, or kiosk layout in Blender. Crea un layout parametrico de entorno.",
        "input_schema": {
            "type": "object",
            "properties": {
                "layout_type": {"type": "string", "enum": ["room", "corridor", "shop", "kiosk"]},
                "collection_name": {"type": "string"},
            },
            "required": ["layout_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_environment_materials",
        "domain": "environment",
        "availability": "server",
        "description": "Apply simple materials to the current environment layout. Aplica materiales simples al entorno.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "load_character_references",
        "domain": "character",
        "availability": "server",
        "description": "Load front, side, and optional back character reference sheets from safe local paths. Carga referencias seguras de personaje.",
        "input_schema": {
            "type": "object",
            "properties": {
                "front": {"type": "string"},
                "side": {"type": "string"},
                "back": {"type": "string"},
            },
            "required": ["front", "side"],
            "additionalProperties": False,
        },
    },
    {
        "name": "clear_character_references",
        "domain": "character",
        "availability": "server",
        "description": "Remove loaded character references from the Blender scene. Elimina referencias cargadas del personaje.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "create_character_blockout",
        "domain": "character",
        "availability": "server",
        "description": "Create a stylized cartoon character blockout in Blender. Crea un blockout de personaje estilizado.",
        "input_schema": {
            "type": "object",
            "properties": {"height": {"type": "number"}, "collection_name": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_character_symmetry",
        "domain": "character",
        "availability": "server",
        "description": "Apply mirror symmetry to the current character meshes. Aplica simetria al personaje actual.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_names": {"type": "array", "items": {"type": "string"}},
                "use_bisect": {"type": "boolean"},
                "use_clip": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "build_character_hair",
        "domain": "character",
        "availability": "server",
        "description": "Build stylized character hair such as a punk or cartoon hairstyle. Construye pelo estilizado para el personaje.",
        "input_schema": {
            "type": "object",
            "properties": {"spike_count": {"type": "integer"}, "collection_name": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "build_character_face",
        "domain": "character",
        "availability": "server",
        "description": "Build stylized character face details. Construye detalles faciales estilizados.",
        "input_schema": {
            "type": "object",
            "properties": {"add_piercings": {"type": "boolean"}, "collection_name": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_character_materials",
        "domain": "character",
        "availability": "server",
        "description": "Apply stylized materials to the current character. Aplica materiales estilizados al personaje.",
        "input_schema": {
            "type": "object",
            "properties": {"include_metal": {"type": "boolean"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "capture_character_review",
        "domain": "character",
        "availability": "server",
        "description": "Capture review images for the current character. Captura vistas de revision del personaje.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "compare_character_with_references",
        "domain": "character",
        "availability": "server",
        "description": "Compare the current character against loaded references. Compara el personaje actual con referencias cargadas.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "apply_character_proportion_fixes",
        "domain": "character",
        "availability": "server",
        "description": "Apply proportion fixes to the current character. Aplica correcciones de proporcion al personaje.",
        "input_schema": {
            "type": "object",
            "properties": {
                "correction_report": {"type": "object"},
                "deltas": {"type": "object"},
                "strength": {"type": "number"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_polyhaven_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Check whether the Poly Haven integration is enabled and ready. Consulta el estado de Poly Haven.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_hyper3d_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Check whether the Hyper3D or Rodin integration is enabled and ready. Consulta el estado de Hyper3D o Rodin.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_sketchfab_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Check whether the Sketchfab integration is enabled and ready. Consulta el estado de Sketchfab.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_hunyuan3d_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Check whether the Hunyuan3D integration is enabled and ready. Consulta el estado de Hunyuan3D.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_polyhaven_categories",
        "domain": "integrations",
        "availability": "server",
        "description": "List available Poly Haven categories for HDRIs, textures, models, or all assets. Lista categorias de Poly Haven.",
        "input_schema": {
            "type": "object",
            "properties": {"asset_type": {"type": "string", "enum": ["hdris", "textures", "models", "all"]}},
            "additionalProperties": False,
        },
    },
    {
        "name": "search_polyhaven_assets",
        "domain": "assets",
        "availability": "server",
        "description": "Search Poly Haven assets from Blender. Busca assets de Poly Haven.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_type": {"type": "string", "enum": ["hdris", "textures", "models", "all"]},
                "categories": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "download_polyhaven_asset",
        "domain": "assets",
        "availability": "server",
        "description": "Download and import a Poly Haven asset into Blender. Descarga e importa un asset de Poly Haven.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "asset_type": {"type": "string"},
                "resolution": {"type": "string"},
                "file_format": {"type": "string"},
            },
            "required": ["asset_id", "asset_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_texture",
        "domain": "assets",
        "availability": "server",
        "description": "Apply a previously imported texture set to a Blender object. Aplica una textura importada a un objeto.",
        "input_schema": {
            "type": "object",
            "properties": {"object_name": {"type": "string"}, "texture_id": {"type": "string"}},
            "required": ["object_name", "texture_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_rodin_job",
        "domain": "integrations",
        "availability": "server",
        "description": "Start a Hyper3D or Rodin generation job from text or image inputs. Inicia un trabajo de Hyper3D o Rodin.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text_prompt": {"type": "string"},
                "images": {"type": "array", "items": {"type": "string"}},
                "bbox_condition": {"type": "array", "items": {"type": "number"}},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "poll_rodin_job_status",
        "domain": "integrations",
        "availability": "server",
        "description": "Poll an existing Hyper3D or Rodin generation job. Consulta el estado de un trabajo de Rodin.",
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
        "description": "Import a generated Hyper3D or Rodin asset into Blender. Importa un asset generado por Rodin.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "task_uuid": {"type": "string"},
                "request_id": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_sketchfab_models",
        "domain": "assets",
        "availability": "server",
        "description": "Search downloadable 3D models on Sketchfab. Busca modelos 3D en Sketchfab.",
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
        "domain": "assets",
        "availability": "server",
        "description": "Fetch preview information for a Sketchfab model. Obtiene la vista previa de un modelo de Sketchfab.",
        "input_schema": {
            "type": "object",
            "properties": {"uid": {"type": "string"}},
            "required": ["uid"],
            "additionalProperties": False,
        },
    },
    {
        "name": "download_sketchfab_model",
        "domain": "assets",
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
        "description": "Start a Hunyuan3D generation workflow from text or image input. Inicia un trabajo de Hunyuan3D.",
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
        "description": "Poll an existing Hunyuan3D generation job. Consulta el estado de un trabajo de Hunyuan3D.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "import_generated_asset_hunyuan",
        "domain": "integrations",
        "availability": "server",
        "description": "Download and import a generated Hunyuan3D asset into Blender. Importa un asset generado por Hunyuan3D.",
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
        "name": "import_asset",
        "domain": "generative",
        "availability": "workflow",
        "description": "Import a supported asset through existing safe integrations such as Poly Haven or Sketchfab. Importa un asset usando integraciones seguras existentes.",
        "input_schema": {
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
    },
    {
        "name": "generate_scene_plan",
        "domain": "generative",
        "availability": "workflow",
        "description": "Generate a safe structured scene plan from a natural-language description. Genera un plan estructurado y seguro a partir de una descripcion.",
        "input_schema": {
            "type": "object",
            "properties": {"description": {"type": "string"}, "style": {"type": "string"}},
            "required": ["description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_scene_plan",
        "domain": "generative",
        "availability": "workflow",
        "description": "Apply a previously generated scene plan using safe primitive and blockout tools. Aplica un plan de escena usando herramientas seguras.",
        "input_schema": {
            "type": "object",
            "properties": {"plan": {"type": "object"}},
            "required": ["plan"],
            "additionalProperties": False,
        },
    },
    {
        "name": "build_scene_from_description",
        "domain": "generative",
        "availability": "workflow",
        "description": "Create a simple Blender scene from a natural-language description using safe parametric steps. Crea una escena simple desde lenguaje natural.",
        "input_schema": {
            "type": "object",
            "properties": {"description": {"type": "string"}, "style": {"type": "string"}},
            "required": ["description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "build_character_from_description",
        "domain": "generative",
        "availability": "workflow",
        "description": "Create a stylized character from a natural-language description using safe character blockout and review steps. Crea un personaje estilizado desde lenguaje natural.",
        "input_schema": {
            "type": "object",
            "properties": {"description": {"type": "string"}, "style": {"type": "string"}},
            "required": ["description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_character_from_references",
        "domain": "generative",
        "availability": "workflow",
        "description": "Create a stylized character from safe local reference sheets using real character tools. Crea un personaje estilizado desde referencias locales seguras.",
        "input_schema": {
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
    },
    {
        "name": "review_and_fix_character",
        "domain": "generative",
        "availability": "workflow",
        "description": "Review the current character and apply a safe proportion-fix pass. Revisa el personaje actual y aplica correcciones seguras.",
        "input_schema": {
            "type": "object",
            "properties": {"strength": {"type": "number"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "create_shop_scene",
        "domain": "generative",
        "availability": "workflow",
        "description": "Create a simple shop scene using real environment tools and safe materials. Crea una tienda simple con herramientas reales de entorno.",
        "input_schema": {
            "type": "object",
            "properties": {"collection_name": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "list_collections",
        "domain": "scene",
        "availability": "unavailable",
        "description": "Planned future helper. The current Blender server does not implement collection listing as a command.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "create_street_blockout",
        "domain": "environment",
        "availability": "unavailable",
        "description": "Planned future helper. The current Blender server does not implement a dedicated street blockout command.",
        "input_schema": {
            "type": "object",
            "properties": {"collection_name": {"type": "string"}},
            "additionalProperties": False,
        },
    },
]

PRIMITIVE_TOOL_NAMES = {
    tool["name"] for tool in TOOLS if tool["availability"] == "server"
}

GENERATIVE_TOOL_NAMES = {
    tool["name"] for tool in TOOLS if tool["availability"] == "workflow"
}

PROVIDER_GATED_TOOL_NAMES = {
    "get_polyhaven_status",
    "get_hyper3d_status",
    "get_sketchfab_status",
    "get_hunyuan3d_status",
    "get_polyhaven_categories",
    "search_polyhaven_assets",
    "download_polyhaven_asset",
    "set_texture",
    "create_rodin_job",
    "poll_rodin_job_status",
    "import_generated_asset",
    "search_sketchfab_models",
    "get_sketchfab_model_preview",
    "download_sketchfab_model",
    "create_hunyuan_job",
    "poll_hunyuan_job_status",
    "import_generated_asset_hunyuan",
    "import_asset",
}

RESULT_SHAPES = {
    "get_scene_info": "Returns a scene summary with object counts, names, and high-level scene metadata.",
    "get_object_info": "Returns transform, visibility, mesh, and material details for a named Blender object.",
    "get_viewport_screenshot": "Returns screenshot metadata including saved filepath and capture status.",
    "create_primitive": "Returns the created primitive name, transform, collection, and success flag.",
    "move_object": "Returns the updated object location and success flag.",
    "rotate_object": "Returns the updated object rotation and success flag.",
    "scale_object": "Returns the updated object scale and success flag.",
    "apply_material": "Returns the target object name, material name, and success flag.",
    "create_light": "Returns the created light name, type, energy, and success flag.",
    "set_camera": "Returns the camera name, lens, whether it became active, and success flag.",
    "create_prop_blockout": "Returns created prop object names, root object, collection, and success flag.",
    "create_environment_layout": "Returns created environment object names, root object, collection, and success flag.",
    "create_character_blockout": "Returns created character blockout object names and related metadata.",
    "capture_character_review": "Returns review image metadata and saved screenshot paths.",
    "compare_character_with_references": "Returns a comparison report with heuristic character proportion findings.",
    "apply_character_proportion_fixes": "Returns applied proportion adjustments and success information.",
    "generate_scene_plan": "Returns a structured scene plan with environment, props, primitives, lights, camera, and limitations.",
    "apply_scene_plan": "Returns executed plan steps, created objects, and any limitations carried from the plan.",
    "build_scene_from_description": "Returns the generated scene plan execution summary and created scene elements.",
    "build_character_from_description": "Returns executed character-building steps and workflow limitations.",
    "create_character_from_references": "Returns executed reference-loading and character-building steps.",
    "review_and_fix_character": "Returns review screenshots, comparison results, and applied fix steps.",
    "create_shop_scene": "Returns environment creation and material-application steps for a shop scene.",
    "import_asset": "Returns the imported asset result from Poly Haven or Sketchfab.",
}

for tool in TOOLS:
    if tool["availability"] == "server":
        tool["layer"] = "primitive"
    elif tool["availability"] == "workflow":
        tool["layer"] = "generative"
    else:
        tool["layer"] = "unavailable"
    tool["provider_gated"] = tool["name"] in PROVIDER_GATED_TOOL_NAMES
    tool["result_shape"] = RESULT_SHAPES.get(
        tool["name"],
        "Returns a structured JSON object with success data or a structured error payload.",
    )

TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
CALLABLE_TOOLS = [tool for tool in TOOLS if tool["availability"] in {"server", "workflow"}]
CALLABLE_TOOL_NAMES = {tool["name"] for tool in CALLABLE_TOOLS}
SERVER_TOOL_NAMES = {tool["name"] for tool in TOOLS if tool["availability"] == "server"}
WORKFLOW_TOOL_NAMES = {tool["name"] for tool in TOOLS if tool["availability"] == "workflow"}
UNAVAILABLE_TOOLS = [tool for tool in TOOLS if tool["availability"] == "unavailable"]
UNAVAILABLE_TOOL_NAMES = {tool["name"] for tool in UNAVAILABLE_TOOLS}
