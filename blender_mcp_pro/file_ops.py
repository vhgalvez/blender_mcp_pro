import os
import tempfile
import zipfile
from contextlib import suppress
from pathlib import Path

import bpy
import mathutils
import requests


SAFE_BASE_DIR = Path.home() / "BlenderMCP"
SCREENSHOT_DIR = SAFE_BASE_DIR / "screenshots"
DOWNLOAD_DIR = SAFE_BASE_DIR / "downloads"
INPUT_DIR = SAFE_BASE_DIR / "inputs"
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
ALLOWED_SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def ensure_runtime_dirs():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return {"base": SAFE_BASE_DIR, "screenshots": SCREENSHOT_DIR, "downloads": DOWNLOAD_DIR, "inputs": INPUT_DIR}


def create_temp_dir(prefix="blendermcp_"):
    ensure_runtime_dirs()
    return tempfile.mkdtemp(prefix=prefix)


def cleanup_path(path):
    with suppress(Exception):
        if path and os.path.isdir(path):
            import shutil

            shutil.rmtree(path)
        elif path and os.path.exists(path):
            os.remove(path)


def _is_relative_to(path_obj, base_obj):
    try:
        path_obj.relative_to(base_obj)
        return True
    except ValueError:
        return False


def resolve_screenshot_path(requested_path=None, image_format="png"):
    ensure_runtime_dirs()
    image_format = (image_format or "png").lower()
    if image_format == "jpg":
        image_format = "jpeg"
    extension = ".jpg" if image_format == "jpeg" else f".{image_format}"
    if extension not in ALLOWED_SCREENSHOT_EXTENSIONS:
        raise ValueError("Unsupported screenshot format")

    if requested_path:
        candidate = Path(requested_path)
        if not candidate.is_absolute():
            candidate = SCREENSHOT_DIR / candidate
        candidate = candidate.resolve(strict=False)
    else:
        candidate = (SCREENSHOT_DIR / f"screenshot_{next(tempfile._get_candidate_names())}{extension}").resolve(strict=False)

    if candidate.suffix.lower() not in ALLOWED_SCREENSHOT_EXTENSIONS:
        raise ValueError("Screenshot file extension is not allowed")
    if not _is_relative_to(candidate, SCREENSHOT_DIR.resolve()):
        raise ValueError(f"Screenshot path must stay inside {SCREENSHOT_DIR}")
    return str(candidate)


def parse_safe_roots(raw_value):
    ensure_runtime_dirs()
    roots = []
    seen = set()

    for default_root in [INPUT_DIR]:
        resolved = default_root.resolve()
        if str(resolved) not in seen:
            roots.append(resolved)
            seen.add(str(resolved))

    if raw_value:
        for part in str(raw_value).split(os.pathsep):
            candidate = part.strip()
            if not candidate:
                continue
            resolved = Path(candidate).expanduser().resolve(strict=False)
            if str(resolved) not in seen:
                roots.append(resolved)
                seen.add(str(resolved))

    return roots


def validate_local_input_path(path, allowed_extensions=None, allowed_roots=None, max_size_mb=25):
    if not path or not isinstance(path, str):
        raise ValueError("Path must be a non-empty string")

    candidate = Path(path).expanduser().resolve(strict=True)
    if not candidate.is_file():
        raise ValueError("Path must point to a file")
    if candidate.is_symlink():
        raise ValueError("Symlinked input files are not allowed")

    roots = allowed_roots or parse_safe_roots("")
    if not any(_is_relative_to(candidate, Path(root).resolve()) for root in roots):
        raise ValueError("Local file access is restricted to configured safe roots")

    if allowed_extensions and candidate.suffix.lower() not in allowed_extensions:
        raise ValueError(f"Unsupported file type: {candidate.suffix}")

    size_limit = max_size_mb * 1024 * 1024
    if candidate.stat().st_size > size_limit:
        raise ValueError(f"File exceeds {max_size_mb} MB limit")

    return str(candidate)


def safe_join(base_dir, relative_path):
    base = Path(base_dir).resolve()
    target = (base / relative_path).resolve(strict=False)
    if not _is_relative_to(target, base):
        raise ValueError("Path escapes the target directory")
    return target


def download_to_file(url, destination_path, headers=None, timeout=(10, 60), max_bytes=200 * 1024 * 1024):
    written = 0
    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            with open(destination_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > max_bytes:
                        raise ValueError("Download exceeded size limit")
                    handle.write(chunk)
    except requests.exceptions.Timeout as exc:
        raise ValueError("Download timed out") from exc
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise ValueError(f"Download failed with status {status_code}") from exc
    except requests.exceptions.RequestException as exc:
        raise ValueError("Download failed") from exc
    return destination_path


def safe_extract_zip(zip_path, destination_dir, max_members=512, max_uncompressed_bytes=500 * 1024 * 1024):
    extracted_paths = []
    total_uncompressed = 0
    base_dir = Path(destination_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:
        members = archive.infolist()
        if len(members) > max_members:
            raise ValueError("Archive contains too many files")

        for info in members:
            if info.is_dir():
                continue

            total_uncompressed += info.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise ValueError("Archive exceeds uncompressed size limit")

            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("Archive symlinks are not allowed")

            member_name = info.filename.replace("\\", "/")
            if member_name.startswith("/") or member_name.startswith("../") or "/../" in member_name:
                raise ValueError("Archive contains a path traversal attempt")

            target_path = safe_join(base_dir, member_name)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, open(target_path, "wb") as destination:
                destination.write(source.read())
            extracted_paths.append(str(target_path))

    return extracted_paths


def import_gltf(filepath):
    existing_objects = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    bpy.context.view_layer.update()
    return list(set(bpy.data.objects) - existing_objects)


def import_obj(filepath):
    existing_objects = set(bpy.data.objects)
    if bpy.app.version >= (4, 0, 0):
        bpy.ops.wm.obj_import(filepath=filepath)
    else:
        bpy.ops.import_scene.obj(filepath=filepath)
    bpy.context.view_layer.update()
    return list(set(bpy.data.objects) - existing_objects)


def import_blend_objects(filepath):
    imported = []
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.objects = data_from.objects
    for obj in data_to.objects:
        if obj is not None:
            bpy.context.collection.objects.link(obj)
            imported.append(obj)
    bpy.context.view_layer.update()
    return imported


def objects_to_metadata(objects):
    imported_names = [obj.name for obj in objects]
    root_objects = [obj for obj in objects if obj.parent is None]
    all_meshes = []

    def visit(obj):
        if obj.type == "MESH":
            all_meshes.append(obj)
        for child in obj.children:
            visit(child)

    for root in root_objects:
        visit(root)

    result = {"imported_objects": imported_names}
    if not all_meshes:
        return result

    minimum = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    maximum = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    for mesh_obj in all_meshes:
        for corner in mesh_obj.bound_box:
            world_corner = mesh_obj.matrix_world @ mathutils.Vector(corner)
            minimum.x = min(minimum.x, world_corner.x)
            minimum.y = min(minimum.y, world_corner.y)
            minimum.z = min(minimum.z, world_corner.z)
            maximum.x = max(maximum.x, world_corner.x)
            maximum.y = max(maximum.y, world_corner.y)
            maximum.z = max(maximum.z, world_corner.z)

    dimensions = [maximum.x - minimum.x, maximum.y - minimum.y, maximum.z - minimum.z]
    result["world_bounding_box"] = [[minimum.x, minimum.y, minimum.z], [maximum.x, maximum.y, maximum.z]]
    result["dimensions"] = [round(value, 4) for value in dimensions]
    return result


def normalize_imported_objects(objects, target_size):
    root_objects = [obj for obj in objects if obj.parent is None]
    metadata = objects_to_metadata(objects)
    dimensions = metadata.get("dimensions")
    if not dimensions:
        return 1.0

    max_dimension = max(dimensions)
    if max_dimension <= 0:
        return 1.0

    scale_factor = target_size / max_dimension
    for root in root_objects:
        root.scale = (
            root.scale.x * scale_factor,
            root.scale.y * scale_factor,
            root.scale.z * scale_factor,
        )
    bpy.context.view_layer.update()
    return scale_factor
