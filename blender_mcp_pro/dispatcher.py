from pathlib import Path

import bpy
import mathutils

from .character_tools import CharacterTools
from . import file_ops
from .integrations import ProviderIntegrations
from .protocol import COMMAND_SCHEMAS, ProtocolError


class SceneModeTools:
    PROP_COLLECTION_NAME = "PROP_Blockout"
    PROP_ROOT_NAME = "PROP_Root"
    PROP_SYMMETRY_NAME = "PROP_Symmetry_Center"
    ENV_COLLECTION_NAME = "ENV_Layout"
    ENV_ROOT_NAME = "ENV_Root"

    def _ensure_collection(self, name):
        collection = bpy.data.collections.get(name)
        if collection is None:
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)
        return collection

    def _link_only_to_collection(self, obj, collection):
        for current in list(obj.users_collection):
            current.objects.unlink(obj)
        collection.objects.link(obj)

    def _clear_named_hierarchy(self, root_name):
        root = bpy.data.objects.get(root_name)
        if root is None:
            return
        objects = list(root.children_recursive)
        objects.append(root)
        for obj in reversed(objects):
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

    def _create_root(self, root_name, collection, location=(0.0, 0.0, 0.0)):
        self._clear_named_hierarchy(root_name)
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
        root = bpy.context.active_object
        root.name = root_name
        root.empty_display_size = 0.4
        self._link_only_to_collection(root, collection)
        return root

    def _assign_material(self, obj, material):
        if not hasattr(obj.data, "materials"):
            return
        obj.data.materials.clear()
        obj.data.materials.append(material)

    def _get_or_create_material(self, name, base_color, metallic=0.0, roughness=0.6):
        material = bpy.data.materials.get(name)
        if material is None:
            material = bpy.data.materials.new(name=name)
            material.use_nodes = True
        nodes = material.node_tree.nodes
        principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
        if principled is None:
            nodes.clear()
            output = nodes.new(type="ShaderNodeOutputMaterial")
            principled = nodes.new(type="ShaderNodeBsdfPrincipled")
            material.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
        principled.inputs["Base Color"].default_value = (*base_color, 1.0)
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = roughness
        return material

    def create_prop_blockout(self, prop_type, collection_name=None):
        collection = self._ensure_collection(collection_name or self.PROP_COLLECTION_NAME)
        root = self._create_root(self.PROP_ROOT_NAME, collection, location=(0.0, 0.0, 0.5))
        created = []

        def add_cube(name, location, scale_xyz):
            bpy.ops.mesh.primitive_cube_add(location=location)
            obj = bpy.context.active_object
            obj.name = name
            obj.scale = scale_xyz
            obj.parent = root
            self._link_only_to_collection(obj, collection)
            created.append(obj.name)
            return obj

        def add_cylinder(name, location, scale_xyz):
            bpy.ops.mesh.primitive_cylinder_add(location=location)
            obj = bpy.context.active_object
            obj.name = name
            obj.scale = scale_xyz
            obj.parent = root
            self._link_only_to_collection(obj, collection)
            created.append(obj.name)
            return obj

        match prop_type:
            case "chair":
                add_cube("PROP_Chair_Seat", (0.0, 0.0, 0.6), (0.45, 0.45, 0.08))
                add_cube("PROP_Chair_Back", (0.0, -0.37, 1.05), (0.45, 0.08, 0.45))
                for index, coords in enumerate([(-0.34, -0.34), (0.34, -0.34), (-0.34, 0.34), (0.34, 0.34)], start=1):
                    add_cube(f"PROP_Chair_Leg_{index}", (coords[0], coords[1], 0.28), (0.06, 0.06, 0.28))
            case "table":
                add_cube("PROP_Table_Top", (0.0, 0.0, 0.82), (0.9, 0.55, 0.08))
                for index, coords in enumerate([(-0.74, -0.39), (0.74, -0.39), (-0.74, 0.39), (0.74, 0.39)], start=1):
                    add_cube(f"PROP_Table_Leg_{index}", (coords[0], coords[1], 0.38), (0.07, 0.07, 0.38))
            case "crate":
                add_cube("PROP_Crate_Main", (0.0, 0.0, 0.45), (0.45, 0.45, 0.45))
                add_cube("PROP_Crate_Band_X", (0.0, 0.0, 0.45), (0.5, 0.06, 0.5))
                add_cube("PROP_Crate_Band_Y", (0.0, 0.0, 0.45), (0.06, 0.5, 0.5))
            case "weapon":
                add_cylinder("PROP_Weapon_Handle", (0.0, 0.0, 0.42), (0.07, 0.07, 0.42))
                add_cube("PROP_Weapon_Guard", (0.0, 0.0, 0.82), (0.28, 0.06, 0.05))
                add_cube("PROP_Weapon_Blade", (0.0, 0.0, 1.38), (0.08, 0.03, 0.56))
                add_cube("PROP_Weapon_Pommel", (0.0, 0.0, 0.02), (0.11, 0.11, 0.08))
            case _:
                raise ValueError("prop_type must be one of chair, table, crate, weapon")

        bpy.context.view_layer.update()
        return {"success": True, "mode": "props", "prop_type": prop_type, "collection": collection.name, "root": root.name, "objects": created}

    def apply_prop_symmetry(self, object_names=None, use_bisect=False, use_clip=True):
        if object_names:
            targets = [bpy.data.objects.get(name) for name in object_names]
            targets = [obj for obj in targets if obj and obj.type == "MESH"]
        else:
            collection = bpy.data.collections.get(self.PROP_COLLECTION_NAME)
            targets = [obj for obj in collection.objects if obj.type == "MESH"] if collection else []
        if not targets:
            raise ValueError("No prop mesh objects were found for symmetry setup")

        center = bpy.data.objects.get(self.PROP_SYMMETRY_NAME)
        if center is None:
            bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 0.0))
            center = bpy.context.active_object
            center.name = self.PROP_SYMMETRY_NAME

        configured = []
        for obj in targets:
            modifier = next((mod for mod in obj.modifiers if mod.type == "MIRROR"), None)
            if modifier is None:
                modifier = obj.modifiers.new(name="PROP_Mirror", type="MIRROR")
            modifier.use_axis[0] = True
            modifier.use_clip = use_clip
            modifier.use_bisect_axis[0] = use_bisect
            modifier.mirror_object = center
            configured.append(obj.name)
        return {"success": True, "mode": "props", "mirror_center": center.name, "objects": configured, "use_clip": use_clip, "use_bisect": use_bisect}

    def apply_prop_materials(self, include_metal=False):
        materials = {
            "wood": self._get_or_create_material("PROP_Mat_Wood", (0.46, 0.28, 0.15), roughness=0.72),
            "paint": self._get_or_create_material("PROP_Mat_Paint", (0.18, 0.38, 0.72), roughness=0.48),
        }
        if include_metal:
            materials["metal"] = self._get_or_create_material("PROP_Mat_Metal", (0.72, 0.74, 0.78), metallic=0.95, roughness=0.18)

        applied = {}
        for obj in bpy.data.objects:
            if not obj.name.startswith("PROP_") or obj.type != "MESH":
                continue
            material = materials["wood"]
            if "Blade" in obj.name or "Guard" in obj.name or "Pommel" in obj.name:
                material = materials.get("metal", materials["paint"])
            elif "Band" in obj.name:
                material = materials["paint"]
            self._assign_material(obj, material)
            applied[obj.name] = material.name

        return {"success": True, "mode": "props", "materials": {key: value.name for key, value in materials.items()}, "applied": applied}

    def create_environment_layout(self, layout_type, collection_name=None):
        collection = self._ensure_collection(collection_name or self.ENV_COLLECTION_NAME)
        root = self._create_root(self.ENV_ROOT_NAME, collection, location=(0.0, 0.0, 0.0))
        created = []

        def add_cube(name, location, scale_xyz):
            bpy.ops.mesh.primitive_cube_add(location=location)
            obj = bpy.context.active_object
            obj.name = name
            obj.scale = scale_xyz
            obj.parent = root
            self._link_only_to_collection(obj, collection)
            created.append(obj.name)
            return obj

        match layout_type:
            case "room":
                add_cube("ENV_Room_Floor", (0.0, 0.0, 0.0), (3.0, 3.0, 0.05))
                add_cube("ENV_Room_BackWall", (0.0, -3.0, 1.5), (3.0, 0.05, 1.5))
                add_cube("ENV_Room_LeftWall", (-3.0, 0.0, 1.5), (0.05, 3.0, 1.5))
                add_cube("ENV_Room_RightWall", (3.0, 0.0, 1.5), (0.05, 3.0, 1.5))
                add_cube("ENV_Room_Ceiling", (0.0, 0.0, 3.0), (3.0, 3.0, 0.05))
            case "corridor":
                add_cube("ENV_Corridor_Floor", (0.0, 0.0, 0.0), (1.5, 6.0, 0.05))
                add_cube("ENV_Corridor_LeftWall", (-1.5, 0.0, 1.5), (0.05, 6.0, 1.5))
                add_cube("ENV_Corridor_RightWall", (1.5, 0.0, 1.5), (0.05, 6.0, 1.5))
                add_cube("ENV_Corridor_Ceiling", (0.0, 0.0, 3.0), (1.5, 6.0, 0.05))
            case "shop":
                add_cube("ENV_Shop_Floor", (0.0, 0.0, 0.0), (4.0, 3.0, 0.05))
                add_cube("ENV_Shop_BackWall", (0.0, -3.0, 1.6), (4.0, 0.05, 1.6))
                add_cube("ENV_Shop_LeftWall", (-4.0, 0.0, 1.6), (0.05, 3.0, 1.6))
                add_cube("ENV_Shop_RightWall", (4.0, 0.0, 1.6), (0.05, 3.0, 1.6))
                add_cube("ENV_Shop_Counter", (0.0, 1.3, 0.55), (1.5, 0.45, 0.55))
                add_cube("ENV_Shop_Shelf_Left", (-2.8, -1.8, 1.1), (0.3, 0.8, 1.1))
                add_cube("ENV_Shop_Shelf_Right", (2.8, -1.8, 1.1), (0.3, 0.8, 1.1))
            case "kiosk":
                add_cube("ENV_Kiosk_Floor", (0.0, 0.0, 0.0), (2.0, 2.0, 0.05))
                add_cube("ENV_Kiosk_BackPanel", (0.0, -1.9, 1.4), (2.0, 0.05, 1.4))
                add_cube("ENV_Kiosk_LeftPanel", (-1.9, 0.0, 1.2), (0.05, 2.0, 1.2))
                add_cube("ENV_Kiosk_RightPanel", (1.9, 0.0, 1.2), (0.05, 2.0, 1.2))
                add_cube("ENV_Kiosk_Counter", (0.0, 1.0, 0.6), (1.5, 0.45, 0.6))
                add_cube("ENV_Kiosk_Canopy", (0.0, 0.0, 2.5), (2.0, 2.0, 0.08))
            case _:
                raise ValueError("layout_type must be one of room, corridor, shop, kiosk")

        bpy.context.view_layer.update()
        return {"success": True, "mode": "environment", "layout_type": layout_type, "collection": collection.name, "root": root.name, "objects": created}

    def apply_environment_materials(self):
        materials = {
            "floor": self._get_or_create_material("ENV_Mat_Floor", (0.58, 0.58, 0.56), roughness=0.82),
            "wall": self._get_or_create_material("ENV_Mat_Wall", (0.82, 0.80, 0.74), roughness=0.88),
            "counter": self._get_or_create_material("ENV_Mat_Counter", (0.36, 0.25, 0.14), roughness=0.64),
            "accent": self._get_or_create_material("ENV_Mat_Accent", (0.16, 0.52, 0.48), roughness=0.55),
        }
        applied = {}
        for obj in bpy.data.objects:
            if not obj.name.startswith("ENV_") or obj.type != "MESH":
                continue
            if "Floor" in obj.name:
                material = materials["floor"]
            elif "Counter" in obj.name:
                material = materials["counter"]
            elif "Shelf" in obj.name or "Canopy" in obj.name:
                material = materials["accent"]
            else:
                material = materials["wall"]
            self._assign_material(obj, material)
            applied[obj.name] = material.name
        return {"success": True, "mode": "environment", "materials": {key: value.name for key, value in materials.items()}, "applied": applied}


class CommandDispatcher:
    def __init__(self, addon_module_name, main_thread_call):
        self.addon_module_name = addon_module_name
        self.main_thread_call = main_thread_call
        self.integrations = ProviderIntegrations()
        self.character_tools = CharacterTools()
        self.scene_mode_tools = SceneModeTools()

    def dispatch(self, command_name, params):
        self.validate(command_name, params)
        handler = getattr(self, f"cmd_{command_name}", None)
        if handler is None:
            raise ProtocolError("unknown_command", f"Unknown command: {command_name}")
        try:
            return handler(**params)
        except ProtocolError:
            raise
        except (ValueError, RuntimeError) as exc:
            raise ProtocolError("command_failed", str(exc)) from exc

    def validate(self, command_name, params):
        schema = COMMAND_SCHEMAS.get(command_name)
        if schema is None:
            raise ProtocolError("unknown_command", f"Unknown command: {command_name}")

        allowed = schema.get("params", {})
        required = schema.get("required", set())
        extra = set(params) - set(allowed)
        if extra:
            raise ProtocolError("invalid_params", f"Unexpected params for {command_name}: {sorted(extra)}")

        missing = [name for name in required if name not in params]
        if missing:
            raise ProtocolError("invalid_params", f"Missing required params for {command_name}: {missing}")

        for name, value in params.items():
            expected = allowed[name]
            if not isinstance(value, expected):
                raise ProtocolError("invalid_params", f"Param '{name}' must be {expected.__name__}")

    def _get_prefs(self):
        def read_prefs():
            addon = bpy.context.preferences.addons.get(self.addon_module_name)
            if not addon:
                raise RuntimeError("Addon preferences are unavailable")
            prefs = addon.preferences
            return {
                "telemetry_consent": prefs.telemetry_consent,
                "hyper3d_api_key": prefs.hyper3d_api_key,
                "sketchfab_api_key": prefs.sketchfab_api_key,
                "hunyuan_secret_id": prefs.hunyuan_secret_id,
                "hunyuan_secret_key": prefs.hunyuan_secret_key,
                "safe_file_roots": prefs.safe_file_roots,
            }

        return self.main_thread_call(read_prefs)

    def _get_scene_flags(self):
        def read_scene():
            scene = bpy.context.scene
            return {
                "use_polyhaven": scene.blendermcp_use_polyhaven,
                "use_hyper3d": scene.blendermcp_use_hyper3d,
                "hyper3d_mode": scene.blendermcp_hyper3d_mode,
                "use_sketchfab": scene.blendermcp_use_sketchfab,
                "use_hunyuan3d": scene.blendermcp_use_hunyuan3d,
                "hunyuan3d_mode": scene.blendermcp_hunyuan3d_mode,
                "hunyuan3d_api_url": scene.blendermcp_hunyuan3d_api_url,
                "hunyuan3d_octree_resolution": scene.blendermcp_hunyuan3d_octree_resolution,
                "hunyuan3d_num_inference_steps": scene.blendermcp_hunyuan3d_num_inference_steps,
                "hunyuan3d_guidance_scale": scene.blendermcp_hunyuan3d_guidance_scale,
                "hunyuan3d_texture": scene.blendermcp_hunyuan3d_texture,
            }

        return self.main_thread_call(read_scene)

    def _validate_mode(self, mode, expected):
        if mode is None:
            return
        if mode != expected:
            raise ValueError(f"mode must be '{expected}'")

    def _get_aabb(self, obj):
        local_bbox_corners = [mathutils.Vector(corner) for corner in obj.bound_box]
        world_bbox_corners = [obj.matrix_world @ corner for corner in local_bbox_corners]
        min_corner = mathutils.Vector(map(min, zip(*world_bbox_corners)))
        max_corner = mathutils.Vector(map(max, zip(*world_bbox_corners)))
        return [[*min_corner], [*max_corner]]

    def cmd_get_scene_info(self):
        def run():
            scene = bpy.context.scene
            scene_info = {
                "name": scene.name,
                "object_count": len(scene.objects),
                "objects": [],
                "materials_count": len(bpy.data.materials),
            }
            for index, obj in enumerate(scene.objects):
                if index >= 10:
                    break
                scene_info["objects"].append(
                    {
                        "name": obj.name,
                        "type": obj.type,
                        "location": [round(float(obj.location.x), 2), round(float(obj.location.y), 2), round(float(obj.location.z), 2)],
                    }
                )
            return scene_info

        return self.main_thread_call(run)

    def cmd_get_object_info(self, name):
        def run():
            obj = bpy.data.objects.get(name)
            if not obj:
                raise ValueError(f"Object not found: {name}")
            info = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
                "visible": obj.visible_get(),
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
            }
            if obj.type == "MESH":
                info["world_bounding_box"] = self._get_aabb(obj)
                info["mesh"] = {
                    "vertices": len(obj.data.vertices),
                    "edges": len(obj.data.edges),
                    "polygons": len(obj.data.polygons),
                }
            return info

        return self.main_thread_call(run)

    def cmd_get_viewport_screenshot(self, filepath=None, format="png", max_size=800):
        safe_path = file_ops.resolve_screenshot_path(filepath, format)

        def run():
            area = next((area for area in bpy.context.screen.areas if area.type == "VIEW_3D"), None)
            if area is None:
                raise ValueError("No 3D viewport found")
            with bpy.context.temp_override(area=area):
                bpy.ops.screen.screenshot_area(filepath=safe_path)

            image = bpy.data.images.load(safe_path)
            width, height = image.size
            if max(width, height) > max_size:
                scale = max_size / max(width, height)
                image.scale(int(width * scale), int(height * scale))
                image.file_format = format.upper()
                image.save()
                width, height = image.size
            bpy.data.images.remove(image)
            return {"success": True, "filepath": safe_path, "width": width, "height": height}

        return self.main_thread_call(run)

    def cmd_get_telemetry_consent(self):
        prefs = self._get_prefs()
        return {"consent": prefs["telemetry_consent"]}

    def cmd_get_polyhaven_status(self):
        flags = self._get_scene_flags()
        return {"enabled": flags["use_polyhaven"], "message": "PolyHaven integration is enabled and ready to use." if flags["use_polyhaven"] else "PolyHaven integration is disabled."}

    def cmd_get_hyper3d_status(self):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        enabled = flags["use_hyper3d"] and bool(prefs["hyper3d_api_key"])
        if enabled:
            return {"enabled": True, "mode": flags["hyper3d_mode"], "message": f"Hyper3D Rodin integration is enabled and ready to use. Mode: {flags['hyper3d_mode']}."}
        if flags["use_hyper3d"]:
            return {"enabled": False, "mode": flags["hyper3d_mode"], "message": "Hyper3D is enabled, but the API key is missing in add-on preferences."}
        return {"enabled": False, "message": "Hyper3D integration is disabled."}

    def cmd_get_sketchfab_status(self):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_sketchfab"]:
            return {"enabled": False, "message": "Sketchfab integration is disabled."}
        if not prefs["sketchfab_api_key"]:
            return {"enabled": False, "message": "Sketchfab is enabled, but the API key is missing in add-on preferences."}
        return self.integrations.test_sketchfab_key(prefs["sketchfab_api_key"])

    def cmd_get_hunyuan3d_status(self):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_hunyuan3d"]:
            return {"enabled": False, "message": "Hunyuan3D integration is disabled."}
        if flags["hunyuan3d_mode"] == "OFFICIAL_API":
            enabled = bool(prefs["hunyuan_secret_id"] and prefs["hunyuan_secret_key"])
            return {"enabled": enabled, "mode": flags["hunyuan3d_mode"], "message": "Hunyuan3D official API is ready." if enabled else "Hunyuan3D official API secrets are missing in add-on preferences."}
        enabled = bool(flags["hunyuan3d_api_url"])
        return {"enabled": enabled, "mode": flags["hunyuan3d_mode"], "message": "Hunyuan3D local API is ready." if enabled else "Hunyuan3D local API URL is missing."}

    def cmd_get_polyhaven_categories(self, asset_type):
        if asset_type not in {"hdris", "textures", "models", "all"}:
            raise ValueError("asset_type must be one of hdris, textures, models, all")
        return self.integrations.get_polyhaven_categories(asset_type)

    def cmd_search_polyhaven_assets(self, asset_type=None, categories=None):
        if asset_type and asset_type not in {"hdris", "textures", "models", "all"}:
            raise ValueError("asset_type must be one of hdris, textures, models, all")
        return self.integrations.search_polyhaven_assets(asset_type, categories)

    def cmd_download_polyhaven_asset(self, asset_id, asset_type, resolution="1k", file_format=None):
        flags = self._get_scene_flags()
        if not flags["use_polyhaven"]:
            raise ValueError("PolyHaven integration is disabled")
        artifact = self.integrations.download_polyhaven_asset(asset_id, asset_type, resolution, file_format)

        if artifact["kind"] == "hdri":
            try:
                def run():
                    if not bpy.data.worlds:
                        bpy.data.worlds.new("World")
                    world = bpy.data.worlds[0]
                    world.use_nodes = True
                    node_tree = world.node_tree
                    node_tree.nodes.clear()

                    tex_coord = node_tree.nodes.new(type="ShaderNodeTexCoord")
                    mapping = node_tree.nodes.new(type="ShaderNodeMapping")
                    env_tex = node_tree.nodes.new(type="ShaderNodeTexEnvironment")
                    background = node_tree.nodes.new(type="ShaderNodeBackground")
                    output = node_tree.nodes.new(type="ShaderNodeOutputWorld")
                    tex_coord.location = (-800, 0)
                    mapping.location = (-600, 0)
                    env_tex.location = (-400, 0)
                    background.location = (-200, 0)
                    output.location = (0, 0)
                    env_tex.image = bpy.data.images.load(artifact["filepath"])
                    node_tree.links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
                    node_tree.links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
                    node_tree.links.new(env_tex.outputs["Color"], background.inputs["Color"])
                    node_tree.links.new(background.outputs["Background"], output.inputs["Surface"])
                    bpy.context.scene.world = world
                    return {"success": True, "message": f"HDRI {artifact['asset_id']} imported successfully", "image_name": env_tex.image.name}

                return self.main_thread_call(run)
            finally:
                file_ops.cleanup_path(artifact["temp_dir"])

        if artifact["kind"] == "textures":
            try:
                def run():
                    downloaded_maps = {}
                    for map_type, path in artifact["maps"].items():
                        image = bpy.data.images.load(path)
                        image.name = f"{artifact['asset_id']}_{map_type}{Path(path).suffix}"
                        image.pack()
                        try:
                            image.colorspace_settings.name = "sRGB" if map_type.lower() in {"color", "diffuse", "albedo"} else "Non-Color"
                        except Exception:
                            pass
                        downloaded_maps[map_type] = image

                    material = bpy.data.materials.new(name=artifact["asset_id"])
                    material.use_nodes = True
                    nodes = material.node_tree.nodes
                    links = material.node_tree.links
                    nodes.clear()

                    output = nodes.new(type="ShaderNodeOutputMaterial")
                    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
                    tex_coord = nodes.new(type="ShaderNodeTexCoord")
                    mapping = nodes.new(type="ShaderNodeMapping")
                    output.location = (300, 0)
                    principled.location = (0, 0)
                    tex_coord.location = (-800, 0)
                    mapping.location = (-600, 0)
                    mapping.vector_type = "TEXTURE"
                    links.new(principled.outputs[0], output.inputs[0])
                    links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])

                    x_pos = -400
                    y_pos = 300
                    for map_type, image in downloaded_maps.items():
                        tex_node = nodes.new(type="ShaderNodeTexImage")
                        tex_node.location = (x_pos, y_pos)
                        tex_node.image = image
                        links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])
                        lowered = map_type.lower()
                        if lowered in {"color", "diffuse", "albedo"}:
                            links.new(tex_node.outputs["Color"], principled.inputs["Base Color"])
                        elif lowered in {"roughness", "rough"}:
                            links.new(tex_node.outputs["Color"], principled.inputs["Roughness"])
                        elif lowered in {"metallic", "metalness", "metal"}:
                            links.new(tex_node.outputs["Color"], principled.inputs["Metallic"])
                        elif lowered in {"normal", "nor"}:
                            normal_map = nodes.new(type="ShaderNodeNormalMap")
                            normal_map.location = (x_pos + 200, y_pos)
                            links.new(tex_node.outputs["Color"], normal_map.inputs["Color"])
                            links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])
                        y_pos -= 250

                    return {"success": True, "message": f"Texture {artifact['asset_id']} imported as material", "material": material.name, "maps": list(downloaded_maps.keys())}

                return self.main_thread_call(run)
            finally:
                file_ops.cleanup_path(artifact["temp_dir"])

        if artifact["kind"] == "model":
            try:
                def run():
                    if artifact["file_format"] in {"gltf", "glb"}:
                        imported = file_ops.import_gltf(artifact["main_filepath"])
                    elif artifact["file_format"] == "fbx":
                        existing = set(bpy.data.objects)
                        bpy.ops.import_scene.fbx(filepath=artifact["main_filepath"])
                        bpy.context.view_layer.update()
                        imported = list(set(bpy.data.objects) - existing)
                    elif artifact["file_format"] == "obj":
                        imported = file_ops.import_obj(artifact["main_filepath"])
                    elif artifact["file_format"] == "blend":
                        imported = file_ops.import_blend_objects(artifact["main_filepath"])
                    else:
                        raise ValueError("Unsupported model format")
                    return {"success": True, "message": f"Model {artifact['asset_id']} imported successfully", **file_ops.objects_to_metadata(imported)}

                return self.main_thread_call(run)
            finally:
                file_ops.cleanup_path(artifact["temp_dir"])

        raise ValueError("Unsupported PolyHaven artifact type")

    def cmd_set_texture(self, object_name, texture_id):
        def run():
            obj = bpy.data.objects.get(object_name)
            if not obj or not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
                raise ValueError(f"Object {object_name} cannot accept materials")

            texture_images = {}
            for image in bpy.data.images:
                if image.name.startswith(texture_id + "_"):
                    map_type = image.name.split("_")[-1].split(".")[0]
                    image.reload()
                    if not image.packed_file:
                        image.pack()
                    texture_images[map_type] = image

            if not texture_images:
                raise ValueError(f"No texture images found for: {texture_id}")

            material_name = f"{texture_id}_material_{object_name}"
            existing = bpy.data.materials.get(material_name)
            if existing:
                bpy.data.materials.remove(existing)

            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()

            output = nodes.new(type="ShaderNodeOutputMaterial")
            principled = nodes.new(type="ShaderNodeBsdfPrincipled")
            tex_coord = nodes.new(type="ShaderNodeTexCoord")
            mapping = nodes.new(type="ShaderNodeMapping")
            output.location = (600, 0)
            principled.location = (300, 0)
            tex_coord.location = (-800, 0)
            mapping.location = (-600, 0)
            mapping.vector_type = "TEXTURE"
            links.new(principled.outputs[0], output.inputs[0])
            links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])

            x_pos = -400
            y_pos = 300
            for map_type, image in texture_images.items():
                tex_node = nodes.new(type="ShaderNodeTexImage")
                tex_node.location = (x_pos, y_pos)
                tex_node.image = image
                links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])
                lowered = map_type.lower()
                if lowered in {"color", "diffuse", "albedo"}:
                    links.new(tex_node.outputs["Color"], principled.inputs["Base Color"])
                elif lowered in {"roughness", "rough"}:
                    links.new(tex_node.outputs["Color"], principled.inputs["Roughness"])
                elif lowered in {"metallic", "metalness", "metal"}:
                    links.new(tex_node.outputs["Color"], principled.inputs["Metallic"])
                elif lowered in {"normal", "nor", "dx", "gl"}:
                    normal_map = nodes.new(type="ShaderNodeNormalMap")
                    normal_map.location = (x_pos + 200, y_pos)
                    links.new(tex_node.outputs["Color"], normal_map.inputs["Color"])
                    links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])
                y_pos -= 250

            while len(obj.data.materials) > 0:
                obj.data.materials.pop(index=0)
            obj.data.materials.append(material)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.context.view_layer.update()
            return {"success": True, "message": f"Created new material and applied texture {texture_id} to {object_name}", "material": material.name, "maps": list(texture_images.keys())}

        return self.main_thread_call(run)

    def cmd_create_rodin_job(self, text_prompt=None, images=None, bbox_condition=None):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_hyper3d"]:
            raise ValueError("Hyper3D integration is disabled")
        if not prefs["hyper3d_api_key"]:
            raise ValueError("Hyper3D API key is missing")
        return self.integrations.create_rodin_job(flags["hyper3d_mode"], prefs["hyper3d_api_key"], text_prompt, images, bbox_condition)

    def cmd_poll_rodin_job_status(self, subscription_key=None, request_id=None):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_hyper3d"]:
            raise ValueError("Hyper3D integration is disabled")
        return self.integrations.poll_rodin_job_status(flags["hyper3d_mode"], prefs["hyper3d_api_key"], subscription_key, request_id)

    def cmd_import_generated_asset(self, name, task_uuid=None, request_id=None):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_hyper3d"]:
            raise ValueError("Hyper3D integration is disabled")
        artifact = self.integrations.download_rodin_asset(flags["hyper3d_mode"], prefs["hyper3d_api_key"], task_uuid, request_id)
        try:
            def run():
                imported = file_ops.import_gltf(artifact["filepath"])
                if not imported:
                    raise ValueError("No objects were imported")
                mesh_obj = next((obj for obj in imported if obj.type == "MESH"), imported[0])
                mesh_obj.name = name
                if getattr(mesh_obj, "data", None):
                    mesh_obj.data.name = name
                metadata = file_ops.objects_to_metadata(imported)
                return {
                    "succeed": True,
                    "name": mesh_obj.name,
                    "type": mesh_obj.type,
                    "location": [mesh_obj.location.x, mesh_obj.location.y, mesh_obj.location.z],
                    "rotation": [mesh_obj.rotation_euler.x, mesh_obj.rotation_euler.y, mesh_obj.rotation_euler.z],
                    "scale": [mesh_obj.scale.x, mesh_obj.scale.y, mesh_obj.scale.z],
                    **metadata,
                }

            return self.main_thread_call(run)
        finally:
            file_ops.cleanup_path(artifact["temp_dir"])

    def cmd_search_sketchfab_models(self, query, categories=None, count=20, downloadable=True):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_sketchfab"]:
            raise ValueError("Sketchfab integration is disabled")
        if not prefs["sketchfab_api_key"]:
            raise ValueError("Sketchfab API key is missing")
        return self.integrations.search_sketchfab_models(prefs["sketchfab_api_key"], query, categories, count, downloadable)

    def cmd_get_sketchfab_model_preview(self, uid):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_sketchfab"]:
            raise ValueError("Sketchfab integration is disabled")
        if not prefs["sketchfab_api_key"]:
            raise ValueError("Sketchfab API key is missing")
        return self.integrations.get_sketchfab_model_preview(prefs["sketchfab_api_key"], uid)

    def cmd_download_sketchfab_model(self, uid, normalize_size=False, target_size=1.0):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_sketchfab"]:
            raise ValueError("Sketchfab integration is disabled")
        if not prefs["sketchfab_api_key"]:
            raise ValueError("Sketchfab API key is missing")
        artifact = self.integrations.download_sketchfab_model(prefs["sketchfab_api_key"], uid)
        try:
            def run():
                imported = file_ops.import_gltf(artifact["main_filepath"])
                scale_applied = 1.0
                if normalize_size:
                    scale_applied = file_ops.normalize_imported_objects(imported, target_size)
                result = {"success": True, "message": "Model imported successfully", **file_ops.objects_to_metadata(imported)}
                if normalize_size:
                    result["normalized"] = True
                    result["scale_applied"] = round(scale_applied, 6)
                return result

            return self.main_thread_call(run)
        finally:
            file_ops.cleanup_path(artifact["temp_dir"])

    def cmd_create_hunyuan_job(self, text_prompt=None, image=None):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if not flags["use_hunyuan3d"]:
            raise ValueError("Hunyuan3D integration is disabled")

        safe_image = None
        if image and not image.lower().startswith(("http://", "https://")):
            safe_image = file_ops.validate_local_input_path(
                image,
                allowed_extensions=file_ops.ALLOWED_IMAGE_EXTENSIONS,
                allowed_roots=file_ops.parse_safe_roots(prefs["safe_file_roots"]),
            )
        elif image:
            safe_image = image

        if flags["hunyuan3d_mode"] == "OFFICIAL_API":
            if not prefs["hunyuan_secret_id"] or not prefs["hunyuan_secret_key"]:
                raise ValueError("Hunyuan official API secrets are missing")
            return self.integrations.create_hunyuan_job_official(
                prefs["hunyuan_secret_id"],
                prefs["hunyuan_secret_key"],
                text_prompt,
                safe_image,
            )

        artifact = self.integrations.create_hunyuan_job_local(
            flags["hunyuan3d_api_url"],
            text_prompt,
            safe_image,
            flags["hunyuan3d_octree_resolution"],
            flags["hunyuan3d_num_inference_steps"],
            flags["hunyuan3d_guidance_scale"],
            flags["hunyuan3d_texture"],
        )
        try:
            def run():
                imported = file_ops.import_gltf(artifact["filepath"])
                return {"status": "DONE", "message": "Generation and import GLB succeeded", **file_ops.objects_to_metadata(imported)}

            return self.main_thread_call(run)
        finally:
            file_ops.cleanup_path(artifact["temp_dir"])

    def cmd_poll_hunyuan_job_status(self, job_id):
        flags = self._get_scene_flags()
        prefs = self._get_prefs()
        if flags["hunyuan3d_mode"] != "OFFICIAL_API":
            raise ValueError("Polling is only available for the official Hunyuan API")
        if not prefs["hunyuan_secret_id"] or not prefs["hunyuan_secret_key"]:
            raise ValueError("Hunyuan official API secrets are missing")
        return self.integrations.poll_hunyuan_job_status(prefs["hunyuan_secret_id"], prefs["hunyuan_secret_key"], job_id)

    def cmd_import_generated_asset_hunyuan(self, name, zip_file_url):
        if not zip_file_url.lower().startswith(("http://", "https://")):
            raise ValueError("zip_file_url must start with http:// or https://")
        artifact = self.integrations.download_hunyuan_zip(zip_file_url)
        try:
            def run():
                imported = file_ops.import_obj(artifact["filepath"])
                meshes = [obj for obj in imported if obj.type == "MESH"]
                if not meshes:
                    raise ValueError("No mesh objects were imported")
                obj = meshes[0]
                obj.name = name
                metadata = file_ops.objects_to_metadata(imported)
                return {
                    "succeed": True,
                    "name": obj.name,
                    "type": obj.type,
                    "location": [obj.location.x, obj.location.y, obj.location.z],
                    "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                    "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
                    **metadata,
                }

            return self.main_thread_call(run)
        finally:
            file_ops.cleanup_path(artifact["temp_dir"])

    def cmd_load_character_references(self, front, side, back=None, mode=None):
        self._validate_mode(mode, "character")
        prefs = self._get_prefs()
        safe_roots = file_ops.parse_safe_roots(prefs["safe_file_roots"])
        front_path = file_ops.validate_local_input_path(front, allowed_extensions=file_ops.ALLOWED_IMAGE_EXTENSIONS, allowed_roots=safe_roots)
        side_path = file_ops.validate_local_input_path(side, allowed_extensions=file_ops.ALLOWED_IMAGE_EXTENSIONS, allowed_roots=safe_roots)
        back_path = None
        if back:
            back_path = file_ops.validate_local_input_path(back, allowed_extensions=file_ops.ALLOWED_IMAGE_EXTENSIONS, allowed_roots=safe_roots)

        return self.main_thread_call(lambda: self.character_tools.load_character_references(front_path, side_path, back_path))

    def cmd_clear_character_references(self, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(self.character_tools.clear_character_references)

    def cmd_create_character_blockout(self, height=2.0, collection_name=None, mode=None):
        self._validate_mode(mode, "character")
        if height <= 0.0:
            raise ValueError("height must be greater than zero")
        return self.main_thread_call(lambda: self.character_tools.create_character_blockout(height=height, collection_name=collection_name))

    def cmd_apply_character_symmetry(self, object_names=None, use_bisect=False, use_clip=True, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(lambda: self.character_tools.apply_character_symmetry(object_names=object_names, use_bisect=use_bisect, use_clip=use_clip))

    def cmd_build_character_hair(self, spike_count=9, collection_name=None, mode=None):
        self._validate_mode(mode, "character")
        if spike_count < 1:
            raise ValueError("spike_count must be greater than zero")
        return self.main_thread_call(lambda: self.character_tools.build_character_hair(spike_count=spike_count, collection_name=collection_name))

    def cmd_build_character_face(self, add_piercings=False, collection_name=None, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(lambda: self.character_tools.build_character_face(add_piercings=add_piercings, collection_name=collection_name))

    def cmd_apply_character_materials(self, include_metal=False, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(lambda: self.character_tools.apply_character_materials(include_metal=include_metal))

    def cmd_capture_character_review(self, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(self.character_tools.capture_character_review)

    def cmd_compare_character_with_references(self, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(self.character_tools.compare_character_with_references)

    def cmd_apply_character_proportion_fixes(self, correction_report=None, deltas=None, strength=1.0, mode=None):
        self._validate_mode(mode, "character")
        return self.main_thread_call(
            lambda: self.character_tools.apply_character_proportion_fixes(
                correction_report=correction_report,
                deltas=deltas,
                strength=strength,
            )
        )

    def cmd_create_prop_blockout(self, mode, prop_type, collection_name=None):
        self._validate_mode(mode, "props")
        return self.main_thread_call(lambda: self.scene_mode_tools.create_prop_blockout(prop_type=prop_type, collection_name=collection_name))

    def cmd_apply_prop_symmetry(self, mode, object_names=None, use_bisect=False, use_clip=True):
        self._validate_mode(mode, "props")
        return self.main_thread_call(
            lambda: self.scene_mode_tools.apply_prop_symmetry(
                object_names=object_names,
                use_bisect=use_bisect,
                use_clip=use_clip,
            )
        )

    def cmd_apply_prop_materials(self, mode, include_metal=False):
        self._validate_mode(mode, "props")
        return self.main_thread_call(lambda: self.scene_mode_tools.apply_prop_materials(include_metal=include_metal))

    def cmd_create_environment_layout(self, mode, layout_type, collection_name=None):
        self._validate_mode(mode, "environment")
        return self.main_thread_call(
            lambda: self.scene_mode_tools.create_environment_layout(layout_type=layout_type, collection_name=collection_name)
        )

    def cmd_apply_environment_materials(self, mode):
        self._validate_mode(mode, "environment")
        return self.main_thread_call(self.scene_mode_tools.apply_environment_materials)
