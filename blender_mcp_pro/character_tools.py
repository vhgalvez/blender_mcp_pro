from pathlib import Path

import bpy
import mathutils

from . import file_ops


class CharacterTools:
    REFERENCE_COLLECTION_NAME = "CHR_References"
    REFERENCE_ROOT_NAME = "CHR_Reference_Root"
    BLOCKOUT_COLLECTION_NAME = "CHR_Blockout"
    BLOCKOUT_ROOT_NAME = "CHR_Blockout_Root"
    DETAIL_COLLECTION_NAME = "CHR_Details"
    HAIR_ROOT_NAME = "CHR_Hair_Root"
    FACE_ROOT_NAME = "CHR_Face_Root"
    SYMMETRY_EMPTY_NAME = "CHR_Symmetry_Center"
    REVIEW_PREFIX = "character_review"

    def _ensure_collection(self, name):
        collection = bpy.data.collections.get(name)
        if collection is None:
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)
        return collection

    def _get_character_collection(self, preferred_name=None):
        if preferred_name:
            return self._ensure_collection(preferred_name)
        collection = bpy.data.collections.get(self.BLOCKOUT_COLLECTION_NAME)
        if collection is None:
            collection = self._ensure_collection(self.BLOCKOUT_COLLECTION_NAME)
        return collection

    def _get_named_object(self, name):
        return bpy.data.objects.get(name)

    def _get_blockout_root(self):
        root = self._get_named_object(self.BLOCKOUT_ROOT_NAME)
        if root is None:
            raise ValueError("Character blockout root was not found. Create the blockout first.")
        return root

    def _get_head_object(self):
        head = self._get_named_object("CHR_Head")
        if head is None:
            raise ValueError("Character head was not found. Create the blockout first.")
        return head

    def _get_reference_object(self, name):
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError("Character references were not found. Load front and side references first.")
        return obj

    def _link_only_to_collection(self, obj, collection):
        for current in list(obj.users_collection):
            current.objects.unlink(obj)
        collection.objects.link(obj)

    def _clear_collection_objects(self, collection_name):
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            return 0

        removed = 0
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1

        if collection_name in bpy.data.collections and not collection.objects:
            bpy.data.collections.remove(collection)
        return removed

    def _clear_named_hierarchy(self, root_name):
        root = bpy.data.objects.get(root_name)
        if root is None:
            return 0
        objects = list(root.children_recursive)
        objects.append(root)
        for obj in reversed(objects):
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        return len(objects)

    def _create_or_replace_empty(self, name, location, collection, parent=None, display_size=0.35):
        existing = bpy.data.objects.get(name)
        if existing:
            bpy.data.objects.remove(existing, do_unlink=True)
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
        obj = bpy.context.active_object
        obj.name = name
        obj.empty_display_size = display_size
        if parent is not None:
            obj.parent = parent
        self._link_only_to_collection(obj, collection)
        return obj

    def _find_view3d_context(self):
        screen = bpy.context.screen
        if screen is None:
            raise ValueError("No active Blender screen is available")
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = next((space for space in area.spaces if space.type == "VIEW_3D"), None)
            region = next((region for region in area.regions if region.type == "WINDOW"), None)
            if space and region:
                return area, region, space
        raise ValueError("No 3D viewport found")

    def _capture_view_axis(self, axis_type, filepath):
        area, region, space = self._find_view3d_context()
        region_3d = space.region_3d
        previous_perspective = region_3d.view_perspective

        with bpy.context.temp_override(area=area, region=region, space_data=space):
            bpy.ops.view3d.view_axis(type=axis_type, align_active=False)
            region_3d.view_perspective = "ORTHO"
            bpy.ops.view3d.view_selected(use_all_regions=False)
            bpy.ops.screen.screenshot_area(filepath=filepath)

        region_3d.view_perspective = previous_perspective
        image = bpy.data.images.load(filepath, check_existing=False)
        width, height = image.size
        bpy.data.images.remove(image)
        return {"filepath": filepath, "width": width, "height": height, "view": axis_type.lower()}

    def _iter_character_objects(self):
        names = [
            "CHR_Head",
            "CHR_Torso",
            "CHR_Pelvis",
            "CHR_Arm_L",
            "CHR_Arm_R",
            "CHR_Leg_L",
            "CHR_Leg_R",
            "CHR_Shoe_L",
            "CHR_Shoe_R",
        ]
        objects = [bpy.data.objects.get(name) for name in names]
        objects = [obj for obj in objects if obj and obj.type == "MESH"]
        for obj in bpy.data.objects:
            if obj.name == "CHR_Hair_Scalp" or obj.name.startswith("CHR_Hair_Spike_"):
                if obj.type == "MESH":
                    objects.append(obj)
        return objects

    def _projected_bounds(self, objects, axis):
        coords = []
        for obj in objects:
            if obj.type != "MESH":
                continue
            for corner in obj.bound_box:
                world = obj.matrix_world @ mathutils.Vector(corner)
                if axis == "front":
                    coords.append((world.x, world.z))
                elif axis == "side":
                    coords.append((world.y, world.z))
        if not coords:
            raise ValueError("No character mesh objects were found")
        xs = [coord[0] for coord in coords]
        zs = [coord[1] for coord in coords]
        return {
            "min_x": min(xs),
            "max_x": max(xs),
            "min_z": min(zs),
            "max_z": max(zs),
            "width": max(xs) - min(xs),
            "height": max(zs) - min(zs),
        }

    def _reference_image_bbox(self, image):
        width, height = image.size
        step = max(1, min(width, height) // 256)
        pixels = image.pixels[:]
        threshold = 0.08

        def sample(ix, iy):
            index = (iy * width + ix) * 4
            return pixels[index:index + 4]

        corners = [
            sample(0, 0),
            sample(max(width - 1, 0), 0),
            sample(0, max(height - 1, 0)),
            sample(max(width - 1, 0), max(height - 1, 0)),
        ]
        background = [sum(values[channel] for values in corners) / len(corners) for channel in range(3)]

        min_x = width
        max_x = -1
        min_y = height
        max_y = -1

        for y in range(0, height, step):
            for x in range(0, width, step):
                r, g, b, a = sample(x, y)
                color_distance = abs(r - background[0]) + abs(g - background[1]) + abs(b - background[2])
                if a > 0.1 or color_distance > threshold:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            return {"width_ratio": 0.6, "height_ratio": 0.9}

        return {
            "width_ratio": max((max_x - min_x) / max(width, 1), 0.01),
            "height_ratio": max((max_y - min_y) / max(height, 1), 0.01),
        }

    def _reference_silhouette_metrics(self):
        front_plane = self._get_reference_object("CHR_REF_Front")
        side_plane = self._get_reference_object("CHR_REF_Side")
        front_material = front_plane.data.materials[0] if front_plane.data.materials else None
        side_material = side_plane.data.materials[0] if side_plane.data.materials else None
        if not front_material or not side_material:
            raise ValueError("Reference materials are missing")

        def material_image(material):
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    return node.image
            raise ValueError("Reference image is missing")

        front_bbox = self._reference_image_bbox(material_image(front_material))
        side_bbox = self._reference_image_bbox(material_image(side_material))

        front_target_width = front_plane.dimensions.x * front_bbox["width_ratio"]
        front_target_height = front_plane.dimensions.z * front_bbox["height_ratio"]
        side_target_width = side_plane.dimensions.x * side_bbox["width_ratio"]
        side_target_height = side_plane.dimensions.z * side_bbox["height_ratio"]

        return {
            "front": {"target_width": front_target_width, "target_height": front_target_height},
            "side": {"target_width": side_target_width, "target_height": side_target_height},
        }

    def _object_dimension(self, name, axis):
        obj = bpy.data.objects.get(name)
        if obj is None:
            return 0.0
        axis_index = {"x": 0, "y": 1, "z": 2}[axis]
        return obj.dimensions[axis_index]

    def _delta_entry(self, current, target):
        denominator = target if abs(target) > 1e-6 else max(abs(current), 1e-6)
        delta = (target - current) / denominator
        return {"current": round(current, 4), "target": round(target, 4), "delta": round(delta, 4)}

    def _build_correction_report(self):
        objects = self._iter_character_objects()
        front_bounds = self._projected_bounds(objects, "front")
        side_bounds = self._projected_bounds(objects, "side")
        target = self._reference_silhouette_metrics()

        head = self._get_head_object()
        torso = self._get_named_object("CHR_Torso")
        arm_l = self._get_named_object("CHR_Arm_L")
        leg_l = self._get_named_object("CHR_Leg_L")
        hair_root = self._get_named_object(self.HAIR_ROOT_NAME)
        hair_objects = [obj for obj in bpy.data.objects if obj.name == "CHR_Hair_Scalp" or obj.name.startswith("CHR_Hair_Spike_")]

        current_total_height = front_bounds["height"]
        head_target = target["front"]["target_height"] * 0.24
        torso_height_target = target["front"]["target_height"] * 0.31
        torso_width_target = target["front"]["target_width"] * 0.42
        arm_thickness_target = target["front"]["target_width"] * 0.11
        leg_thickness_target = target["front"]["target_width"] * 0.14
        leg_length_target = target["front"]["target_height"] * 0.34
        hair_volume_current = 0.0
        if hair_objects:
            hair_bounds = self._projected_bounds(hair_objects, "front")
            hair_volume_current = max(0.0, hair_bounds["height"] - head.dimensions.z)
        hair_volume_target = target["front"]["target_height"] * 0.12

        silhouette_front_delta = (target["front"]["target_width"] - front_bounds["width"]) / max(target["front"]["target_width"], 1e-6)
        silhouette_side_delta = (target["side"]["target_width"] - side_bounds["width"]) / max(target["side"]["target_width"], 1e-6)
        overall_mismatch = max(abs(silhouette_front_delta), abs(silhouette_side_delta), abs((target["front"]["target_height"] - current_total_height) / max(target["front"]["target_height"], 1e-6)))

        return {
            "head_size": self._delta_entry(head.dimensions.z, head_target),
            "torso_width": self._delta_entry(torso.dimensions.x if torso else 0.0, torso_width_target),
            "torso_height": self._delta_entry(torso.dimensions.z if torso else 0.0, torso_height_target),
            "arm_thickness": self._delta_entry(arm_l.dimensions.x if arm_l else 0.0, arm_thickness_target),
            "leg_thickness": self._delta_entry(leg_l.dimensions.x if leg_l else 0.0, leg_thickness_target),
            "leg_length": self._delta_entry(leg_l.dimensions.z if leg_l else 0.0, leg_length_target),
            "hair_volume": self._delta_entry(hair_volume_current, hair_volume_target),
            "overall_silhouette_mismatch": {
                "front_width_delta": round(silhouette_front_delta, 4),
                "side_width_delta": round(silhouette_side_delta, 4),
                "height_delta": round((target["front"]["target_height"] - current_total_height) / max(target["front"]["target_height"], 1e-6), 4),
                "score": round(overall_mismatch, 4),
            },
            "reference_targets": target,
        }

    def _scale_objects(self, names, scale_xyz):
        adjusted = []
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            obj.scale = (
                obj.scale.x * scale_xyz[0],
                obj.scale.y * scale_xyz[1],
                obj.scale.z * scale_xyz[2],
            )
            adjusted.append(obj.name)
        return adjusted

    def _assign_single_material(self, obj, material):
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

    def _ensure_shoe_objects(self, collection, root):
        created = []
        leg_positions = {"CHR_Shoe_L": (-0.18, 0.04, -0.55), "CHR_Shoe_R": (0.18, 0.04, -0.55)}
        for name, location in leg_positions.items():
            obj = bpy.data.objects.get(name)
            if obj is None:
                bpy.ops.mesh.primitive_cube_add(location=location)
                obj = bpy.context.active_object
                obj.name = name
                obj.scale = (0.16, 0.28, 0.09)
                obj.parent = root
                self._link_only_to_collection(obj, collection)
                created.append(obj.name)
        return created

    def _ensure_reference_material(self, obj, image_path, material_name):
        image = bpy.data.images.load(image_path, check_existing=True)
        material = bpy.data.materials.get(material_name)
        if material is None:
            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True

        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new(type="ShaderNodeOutputMaterial")
        emission = nodes.new(type="ShaderNodeEmission")
        tex = nodes.new(type="ShaderNodeTexImage")
        transparent = nodes.new(type="ShaderNodeBsdfTransparent")
        mix = nodes.new(type="ShaderNodeMixShader")
        output.location = (400, 0)
        mix.location = (200, 0)
        emission.location = (0, 80)
        transparent.location = (0, -100)
        tex.location = (-250, 0)
        tex.image = image
        material.blend_method = "BLEND"
        links.new(tex.outputs["Color"], emission.inputs["Color"])
        links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
        links.new(transparent.outputs["BSDF"], mix.inputs[1])
        links.new(emission.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], output.inputs["Surface"])

        obj.data.materials.clear()
        obj.data.materials.append(material)
        return image

    def _create_reference_plane(self, collection, root, name, image_path, location, rotation):
        image = bpy.data.images.load(image_path, check_existing=True)
        width = max(image.size[0], 1)
        height = max(image.size[1], 1)
        aspect = width / height
        plane_width = 2.0 * aspect
        plane_height = 2.0

        bpy.ops.mesh.primitive_plane_add(size=1.0, location=location, rotation=rotation)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (plane_width, 1.0, plane_height)
        obj.parent = root
        obj.lock_rotation[0] = True
        obj.lock_scale[1] = True
        obj.show_in_front = True
        self._link_only_to_collection(obj, collection)
        self._ensure_reference_material(obj, image_path, f"{name}_Mat")
        return obj

    def load_character_references(self, front_path, side_path, back_path=None):
        self.clear_character_references()

        collection = self._ensure_collection(self.REFERENCE_COLLECTION_NAME)
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 1.0))
        root = bpy.context.active_object
        root.name = self.REFERENCE_ROOT_NAME
        root.empty_display_size = 0.4
        self._link_only_to_collection(root, collection)

        planes = []
        planes.append(
            self._create_reference_plane(
                collection,
                root,
                "CHR_REF_Front",
                front_path,
                location=(0.0, -2.0, 1.0),
                rotation=(1.5708, 0.0, 0.0),
            )
        )
        planes.append(
            self._create_reference_plane(
                collection,
                root,
                "CHR_REF_Side",
                side_path,
                location=(-2.0, 0.0, 1.0),
                rotation=(1.5708, 0.0, 1.5708),
            )
        )
        if back_path:
            planes.append(
                self._create_reference_plane(
                    collection,
                    root,
                    "CHR_REF_Back",
                    back_path,
                    location=(0.0, 2.0, 1.0),
                    rotation=(1.5708, 0.0, 3.14159),
                )
            )

        return {
            "success": True,
            "collection": collection.name,
            "root": root.name,
            "references": [obj.name for obj in planes],
        }

    def clear_character_references(self):
        removed = self._clear_collection_objects(self.REFERENCE_COLLECTION_NAME)
        return {"success": True, "removed_objects": removed}

    def create_character_blockout(self, height=2.0, collection_name=None):
        collection = self._ensure_collection(collection_name or self.BLOCKOUT_COLLECTION_NAME)

        existing_root = bpy.data.objects.get(self.BLOCKOUT_ROOT_NAME)
        if existing_root and existing_root.name in bpy.data.objects:
            bpy.data.objects.remove(existing_root, do_unlink=True)

        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 1.0))
        root = bpy.context.active_object
        root.name = self.BLOCKOUT_ROOT_NAME
        root.empty_display_size = 0.5
        self._link_only_to_collection(root, collection)

        scale = max(height / 2.0, 0.5)

        def add_uv_sphere(name, location, scale_xyz):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=location)
            obj = bpy.context.active_object
            obj.name = name
            obj.scale = scale_xyz
            obj.parent = root
            self._link_only_to_collection(obj, collection)
            return obj

        def add_cylinder(name, location, scale_xyz, rotation=(0.0, 0.0, 0.0)):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0, location=location, rotation=rotation)
            obj = bpy.context.active_object
            obj.name = name
            obj.scale = scale_xyz
            obj.parent = root
            self._link_only_to_collection(obj, collection)
            return obj

        objects = []
        objects.append(add_uv_sphere("CHR_Head", (0.0, 0.0, 1.7 * scale), (0.42 * scale, 0.38 * scale, 0.46 * scale)))
        objects.append(add_cylinder("CHR_Torso", (0.0, 0.0, 1.15 * scale), (0.42 * scale, 0.28 * scale, 0.5 * scale)))
        objects.append(add_uv_sphere("CHR_Pelvis", (0.0, 0.0, 0.65 * scale), (0.34 * scale, 0.24 * scale, 0.2 * scale)))
        objects.append(add_cylinder("CHR_Arm_L", (-0.62 * scale, 0.0, 1.12 * scale), (0.11 * scale, 0.11 * scale, 0.48 * scale), rotation=(0.0, 1.5708, 0.0)))
        objects.append(add_cylinder("CHR_Arm_R", (0.62 * scale, 0.0, 1.12 * scale), (0.11 * scale, 0.11 * scale, 0.48 * scale), rotation=(0.0, 1.5708, 0.0)))
        objects.append(add_cylinder("CHR_Leg_L", (-0.18 * scale, 0.0, 0.1 * scale), (0.13 * scale, 0.13 * scale, 0.58 * scale)))
        objects.append(add_cylinder("CHR_Leg_R", (0.18 * scale, 0.0, 0.1 * scale), (0.13 * scale, 0.13 * scale, 0.58 * scale)))

        bpy.context.view_layer.update()
        return {
            "success": True,
            "collection": collection.name,
            "root": root.name,
            "objects": [obj.name for obj in objects],
            "height": height,
        }

    def apply_character_symmetry(self, object_names=None, use_bisect=False, use_clip=True):
        if object_names:
            targets = [bpy.data.objects.get(name) for name in object_names]
            targets = [obj for obj in targets if obj and obj.type == "MESH"]
        else:
            collection = bpy.data.collections.get(self.BLOCKOUT_COLLECTION_NAME)
            targets = [obj for obj in collection.objects if obj.type == "MESH"] if collection else []

        if not targets:
            raise ValueError("No mesh objects were found for symmetry setup")

        center = bpy.data.objects.get(self.SYMMETRY_EMPTY_NAME)
        if center is None:
            bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 0.0))
            center = bpy.context.active_object
            center.name = self.SYMMETRY_EMPTY_NAME

        configured = []
        for obj in targets:
            modifier = next((mod for mod in obj.modifiers if mod.type == "MIRROR"), None)
            if modifier is None:
                modifier = obj.modifiers.new(name="CHR_Mirror", type="MIRROR")
            modifier.use_axis[0] = True
            modifier.use_axis[1] = False
            modifier.use_axis[2] = False
            modifier.mirror_object = center
            modifier.use_clip = use_clip
            modifier.use_bisect_axis[0] = use_bisect
            configured.append(obj.name)

        return {
            "success": True,
            "mirror_center": center.name,
            "objects": configured,
            "use_clip": use_clip,
            "use_bisect": use_bisect,
        }

    def build_character_hair(self, spike_count=9, collection_name=None):
        head = self._get_head_object()
        root = self._get_blockout_root()
        collection = self._get_character_collection(collection_name or self.DETAIL_COLLECTION_NAME)
        self._clear_named_hierarchy(self.HAIR_ROOT_NAME)

        hair_root = self._create_or_replace_empty(
            self.HAIR_ROOT_NAME,
            location=head.location.copy(),
            collection=collection,
            parent=root,
            display_size=0.3,
        )

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.38, location=(head.location.x, head.location.y, head.location.z + 0.03))
        scalp = bpy.context.active_object
        scalp.name = "CHR_Hair_Scalp"
        scalp.scale = (1.0, 0.92, 0.72)
        scalp.parent = hair_root
        self._link_only_to_collection(scalp, collection)

        spike_count = max(5, min(spike_count, 18))
        spikes = []
        x_positions = [((index / (spike_count - 1)) - 0.5) * 0.7 for index in range(spike_count)]
        for index, x_pos in enumerate(x_positions):
            height = 0.45 + (0.08 if index % 2 == 0 else 0.0)
            rotation_y = (-0.2 + (index / max(spike_count - 1, 1)) * 0.4)
            bpy.ops.mesh.primitive_cone_add(
                radius1=0.11,
                radius2=0.015,
                depth=height,
                location=(head.location.x + x_pos, head.location.y - 0.02, head.location.z + 0.48 + abs(x_pos) * 0.05),
                rotation=(0.12, rotation_y, 0.0),
            )
            spike = bpy.context.active_object
            spike.name = f"CHR_Hair_Spike_{index + 1:02d}"
            spike.parent = hair_root
            self._link_only_to_collection(spike, collection)
            spikes.append(spike.name)

        bpy.context.view_layer.update()
        return {
            "success": True,
            "collection": collection.name,
            "root": hair_root.name,
            "objects": [scalp.name, *spikes],
            "style": "stylized_spiky_punk",
        }

    def build_character_face(self, add_piercings=False, collection_name=None):
        head = self._get_head_object()
        root = self._get_blockout_root()
        collection = self._get_character_collection(collection_name or self.DETAIL_COLLECTION_NAME)
        self._clear_named_hierarchy(self.FACE_ROOT_NAME)

        face_root = self._create_or_replace_empty(
            self.FACE_ROOT_NAME,
            location=head.location.copy(),
            collection=collection,
            parent=root,
            display_size=0.25,
        )

        created = []
        eye_positions = {"CHR_Eye_L": (-0.12, -0.3, 0.08), "CHR_Eye_R": (0.12, -0.3, 0.08)}
        for name, offset in eye_positions.items():
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=0.07,
                location=(head.location.x + offset[0], head.location.y + offset[1], head.location.z + offset[2]),
            )
            eye = bpy.context.active_object
            eye.name = name
            eye.scale = (1.0, 0.65, 1.15)
            eye.parent = face_root
            self._link_only_to_collection(eye, collection)
            created.append(eye.name)

        bpy.ops.mesh.primitive_cone_add(
            radius1=0.04,
            radius2=0.0,
            depth=0.12,
            location=(head.location.x, head.location.y - 0.37, head.location.z - 0.01),
            rotation=(1.5708, 0.0, 0.0),
        )
        nose = bpy.context.active_object
        nose.name = "CHR_Nose"
        nose.parent = face_root
        self._link_only_to_collection(nose, collection)
        created.append(nose.name)

        bpy.ops.curve.primitive_bezier_curve_add(location=(head.location.x, head.location.y - 0.355, head.location.z - 0.17))
        mouth = bpy.context.active_object
        mouth.name = "CHR_Mouth"
        mouth.parent = face_root
        self._link_only_to_collection(mouth, collection)
        mouth.data.dimensions = "3D"
        mouth.data.bevel_depth = 0.01
        mouth.data.resolution_u = 12
        spline = mouth.data.splines[0]
        left_point = spline.bezier_points[0]
        right_point = spline.bezier_points[1]
        left_point.co = (-0.12, 0.0, 0.0)
        right_point.co = (0.12, 0.0, 0.0)
        left_point.handle_right = (-0.04, 0.0, -0.045)
        right_point.handle_left = (0.04, 0.0, -0.045)
        created.append(mouth.name)

        if add_piercings:
            piercing_specs = {
                "CHR_Piercing_Nose": (0.055, -0.4, -0.015),
                "CHR_Piercing_Lip": (-0.05, -0.37, -0.18),
            }
            for name, offset in piercing_specs.items():
                bpy.ops.mesh.primitive_torus_add(
                    major_radius=0.018,
                    minor_radius=0.004,
                    location=(head.location.x + offset[0], head.location.y + offset[1], head.location.z + offset[2]),
                    rotation=(1.5708, 0.0, 0.0),
                )
                ring = bpy.context.active_object
                ring.name = name
                ring.parent = face_root
                self._link_only_to_collection(ring, collection)
                created.append(ring.name)

        bpy.context.view_layer.update()
        return {
            "success": True,
            "collection": collection.name,
            "root": face_root.name,
            "objects": created,
            "piercings": add_piercings,
        }

    def apply_character_materials(self, include_metal=False):
        collection = self._get_character_collection(self.BLOCKOUT_COLLECTION_NAME)
        root = self._get_blockout_root()
        created_shoes = self._ensure_shoe_objects(collection, root)

        materials = {
            "skin": self._get_or_create_material("CHR_Mat_Skin", (0.93, 0.72, 0.60), roughness=0.55),
            "hair": self._get_or_create_material("CHR_Mat_Hair", (0.10, 0.09, 0.11), roughness=0.42),
            "shirt": self._get_or_create_material("CHR_Mat_Shirt", (0.16, 0.27, 0.62), roughness=0.62),
            "pants": self._get_or_create_material("CHR_Mat_Pants", (0.12, 0.12, 0.14), roughness=0.75),
            "shoes": self._get_or_create_material("CHR_Mat_Shoes", (0.05, 0.05, 0.05), roughness=0.38),
            "eyes": self._get_or_create_material("CHR_Mat_Eyes", (0.96, 0.97, 1.0), roughness=0.22),
        }
        if include_metal:
            materials["metal"] = self._get_or_create_material("CHR_Mat_Metal", (0.72, 0.74, 0.78), metallic=0.95, roughness=0.18)

        assignments = {
            "skin": ["CHR_Head", "CHR_Arm_L", "CHR_Arm_R", "CHR_Nose", "CHR_Mouth"],
            "hair": ["CHR_Hair_Scalp"],
            "shirt": ["CHR_Torso"],
            "pants": ["CHR_Pelvis", "CHR_Leg_L", "CHR_Leg_R"],
            "shoes": ["CHR_Shoe_L", "CHR_Shoe_R"],
            "eyes": ["CHR_Eye_L", "CHR_Eye_R"],
        }

        for obj in bpy.data.objects:
            if obj.name.startswith("CHR_Hair_Spike_"):
                assignments["hair"].append(obj.name)
            if obj.name.startswith("CHR_Piercing_") and include_metal:
                assignments.setdefault("metal", []).append(obj.name)

        applied = {}
        for material_key, object_names in assignments.items():
            material = materials.get(material_key)
            if material is None:
                continue
            for name in object_names:
                obj = bpy.data.objects.get(name)
                if obj is None:
                    continue
                self._assign_single_material(obj, material)
                applied[name] = material.name

        return {
            "success": True,
            "materials": {key: material.name for key, material in materials.items()},
            "applied": applied,
            "created_shoes": created_shoes,
        }

    def capture_character_review(self):
        self._get_head_object()
        file_ops.ensure_runtime_dirs()
        front_path = file_ops.resolve_screenshot_path(f"{self.REVIEW_PREFIX}_front.png", "png")
        side_path = file_ops.resolve_screenshot_path(f"{self.REVIEW_PREFIX}_side.png", "png")

        front = self._capture_view_axis("FRONT", front_path)
        side = self._capture_view_axis("RIGHT", side_path)
        return {
            "success": True,
            "screenshots": {
                "front": front,
                "side": side,
            },
        }

    def compare_character_with_references(self):
        report = self._build_correction_report()
        return {
            "success": True,
            "report": report,
            "notes": "Reference comparison uses simple silhouette envelopes and stylized proportion heuristics.",
        }

    def apply_character_proportion_fixes(self, correction_report=None, deltas=None, strength=1.0):
        if correction_report is None and deltas is None:
            correction_report = self._build_correction_report()

        report = correction_report or {}
        deltas = dict(deltas or {})
        if not deltas:
            for key in ["head_size", "torso_width", "torso_height", "arm_thickness", "leg_thickness", "leg_length", "hair_volume"]:
                entry = report.get(key)
                if isinstance(entry, dict) and "delta" in entry:
                    deltas[key] = entry["delta"]

        strength = max(0.0, min(strength, 1.0))
        adjustments = {}

        def factor(delta):
            return max(0.6, min(1.4, 1.0 + (delta * strength)))

        if "head_size" in deltas:
            scale = factor(deltas["head_size"])
            adjustments["head_size"] = self._scale_objects(["CHR_Head"], (scale, scale, scale))
        if "torso_width" in deltas:
            scale = factor(deltas["torso_width"])
            adjustments["torso_width"] = self._scale_objects(["CHR_Torso"], (scale, 1.0, 1.0))
        if "torso_height" in deltas:
            scale = factor(deltas["torso_height"])
            adjustments["torso_height"] = self._scale_objects(["CHR_Torso"], (1.0, 1.0, scale))
        if "arm_thickness" in deltas:
            scale = factor(deltas["arm_thickness"])
            adjustments["arm_thickness"] = self._scale_objects(["CHR_Arm_L", "CHR_Arm_R"], (scale, scale, 1.0))
        if "leg_thickness" in deltas:
            scale = factor(deltas["leg_thickness"])
            adjustments["leg_thickness"] = self._scale_objects(["CHR_Leg_L", "CHR_Leg_R"], (scale, scale, 1.0))
        if "leg_length" in deltas:
            scale = factor(deltas["leg_length"])
            adjustments["leg_length"] = self._scale_objects(["CHR_Leg_L", "CHR_Leg_R"], (1.0, 1.0, scale))
            for shoe_name in ["CHR_Shoe_L", "CHR_Shoe_R"]:
                shoe = bpy.data.objects.get(shoe_name)
                if shoe:
                    shoe.location.z *= scale
        if "hair_volume" in deltas:
            scale = factor(deltas["hair_volume"])
            hair_targets = [obj.name for obj in bpy.data.objects if obj.name == "CHR_Hair_Scalp" or obj.name.startswith("CHR_Hair_Spike_")]
            adjustments["hair_volume"] = self._scale_objects(hair_targets, (scale, scale, scale))

        bpy.context.view_layer.update()
        return {
            "success": True,
            "applied_deltas": {key: round(value, 4) for key, value in deltas.items()},
            "adjustments": adjustments,
            "strength": strength,
        }
