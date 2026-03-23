import base64
import hashlib
import hmac
import json
import os
import re
from datetime import datetime

import requests

from . import file_ops


REQ_HEADERS = requests.utils.default_headers()
REQ_HEADERS.update({"User-Agent": "blender-mcp"})


class ProviderIntegrations:
    def __init__(self):
        self.default_timeout = (10, 60)
        self.long_timeout = (10, 120)
        self.generation_timeout = (10, 180)
        self.download_timeout = (10, 90)

    def _request(self, method, url, timeout=None, error_context="request", **kwargs):
        timeout = timeout or self.default_timeout
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as exc:
            raise ValueError(f"{error_context} timed out") from exc
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise ValueError(f"{error_context} failed with status {status_code}") from exc
        except requests.exceptions.RequestException as exc:
            raise ValueError(f"{error_context} failed") from exc

    def get_polyhaven_categories(self, asset_type):
        response = self._request(
            "GET",
            f"https://api.polyhaven.com/categories/{asset_type}",
            headers=REQ_HEADERS,
            timeout=self.default_timeout,
            error_context="PolyHaven category request",
        )
        return {"categories": response.json()}

    def search_polyhaven_assets(self, asset_type=None, categories=None):
        params = {}
        if asset_type and asset_type != "all":
            params["type"] = asset_type
        if categories:
            params["categories"] = categories
        response = self._request(
            "GET",
            "https://api.polyhaven.com/assets",
            params=params,
            headers=REQ_HEADERS,
            timeout=self.default_timeout,
            error_context="PolyHaven asset search",
        )
        assets = response.json()
        limited_assets = {}
        for index, (key, value) in enumerate(assets.items()):
            if index >= 20:
                break
            limited_assets[key] = value
        return {"assets": limited_assets, "total_count": len(assets), "returned_count": len(limited_assets)}

    def download_polyhaven_asset(self, asset_id, asset_type, resolution="1k", file_format=None):
        response = self._request(
            "GET",
            f"https://api.polyhaven.com/files/{asset_id}",
            headers=REQ_HEADERS,
            timeout=self.default_timeout,
            error_context="PolyHaven file manifest request",
        )
        files_data = response.json()

        if asset_type == "hdris":
            file_format = file_format or "hdr"
            file_info = files_data.get("hdri", {}).get(resolution, {}).get(file_format)
            if not file_info:
                raise ValueError("Requested HDRI format or resolution is unavailable")
            temp_dir = file_ops.create_temp_dir("blendermcp_hdri_")
            file_path = os.path.join(temp_dir, f"{asset_id}.{file_format}")
            file_ops.download_to_file(file_info["url"], file_path, headers=REQ_HEADERS)
            return {"kind": "hdri", "asset_id": asset_id, "filepath": file_path, "temp_dir": temp_dir}

        if asset_type == "textures":
            file_format = file_format or "jpg"
            temp_dir = file_ops.create_temp_dir("blendermcp_tex_")
            maps = {}
            for map_type, resolutions in files_data.items():
                if map_type in {"blend", "gltf"}:
                    continue
                file_info = resolutions.get(resolution, {}).get(file_format)
                if not file_info:
                    continue
                path = os.path.join(temp_dir, f"{asset_id}_{map_type}.{file_format}")
                file_ops.download_to_file(file_info["url"], path, headers=REQ_HEADERS)
                maps[map_type] = path
            if not maps:
                file_ops.cleanup_path(temp_dir)
                raise ValueError("No texture maps found for the requested resolution and format")
            return {"kind": "textures", "asset_id": asset_id, "maps": maps, "temp_dir": temp_dir}

        if asset_type == "models":
            file_format = file_format or "gltf"
            if file_format == "blend":
                raise ValueError("Remote .blend imports are disabled")
            resolution_data = files_data.get(file_format, {}).get(resolution)
            if not resolution_data or file_format not in resolution_data:
                raise ValueError("Requested model format or resolution is unavailable")

            file_info = resolution_data[file_format]
            temp_dir = file_ops.create_temp_dir("blendermcp_model_")
            main_name = file_info["url"].split("/")[-1]
            main_path = os.path.join(temp_dir, main_name)
            file_ops.download_to_file(file_info["url"], main_path, headers=REQ_HEADERS)

            for include_path, include_info in (file_info.get("include") or {}).items():
                safe_path = file_ops.safe_join(temp_dir, include_path)
                safe_path.parent.mkdir(parents=True, exist_ok=True)
                file_ops.download_to_file(include_info["url"], str(safe_path), headers=REQ_HEADERS)

            return {
                "kind": "model",
                "asset_id": asset_id,
                "main_filepath": main_path,
                "file_format": file_format,
                "temp_dir": temp_dir,
            }

        raise ValueError(f"Unsupported asset type: {asset_type}")

    def test_sketchfab_key(self, api_key):
        response = self._request(
            "GET",
            "https://api.sketchfab.com/v3/me",
            headers={"Authorization": f"Token {api_key}"},
            timeout=self.default_timeout,
            error_context="Sketchfab auth check",
        )
        username = response.json().get("username", "Unknown user")
        return {"enabled": True, "message": f"Sketchfab integration is enabled and ready to use. Logged in as: {username}"}

    def search_sketchfab_models(self, api_key, query, categories=None, count=20, downloadable=True):
        params = {
            "type": "models",
            "q": query,
            "count": count,
            "downloadable": downloadable,
            "archives_flavours": False,
        }
        if categories:
            params["categories"] = categories
        response = self._request(
            "GET",
            "https://api.sketchfab.com/v3/search",
            headers={"Authorization": f"Token {api_key}"},
            params=params,
            timeout=self.default_timeout,
            error_context="Sketchfab model search",
        )
        return response.json()

    def get_sketchfab_model_preview(self, api_key, uid):
        response = self._request(
            "GET",
            f"https://api.sketchfab.com/v3/models/{uid}",
            headers={"Authorization": f"Token {api_key}"},
            timeout=self.default_timeout,
            error_context="Sketchfab model lookup",
        )
        data = response.json()
        thumbnails = data.get("thumbnails", {}).get("images", [])
        if not thumbnails:
            raise ValueError("No thumbnail available for this model")

        selected = None
        for thumb in thumbnails:
            width = thumb.get("width", 0)
            if 400 <= width <= 800:
                selected = thumb
                break
        selected = selected or thumbnails[0]

        thumb_response = self._request(
            "GET",
            selected["url"],
            timeout=self.default_timeout,
            error_context="Sketchfab thumbnail download",
        )
        content_type = thumb_response.headers.get("Content-Type", "")
        image_format = "png" if "png" in content_type or selected["url"].endswith(".png") else "jpeg"
        return {
            "success": True,
            "image_data": base64.b64encode(thumb_response.content).decode("ascii"),
            "format": image_format,
            "model_name": data.get("name", "Unknown"),
            "author": data.get("user", {}).get("username", "Unknown"),
            "uid": uid,
            "thumbnail_width": selected.get("width"),
            "thumbnail_height": selected.get("height"),
        }

    def download_sketchfab_model(self, api_key, uid):
        response = self._request(
            "GET",
            f"https://api.sketchfab.com/v3/models/{uid}/download",
            headers={"Authorization": f"Token {api_key}"},
            timeout=self.default_timeout,
            error_context="Sketchfab download request",
        )
        download_url = response.json().get("gltf", {}).get("url")
        if not download_url:
            raise ValueError("No glTF download URL is available for this model")

        temp_dir = file_ops.create_temp_dir("blendermcp_sketchfab_")
        zip_path = os.path.join(temp_dir, f"{uid}.zip")
        file_ops.download_to_file(download_url, zip_path, timeout=self.download_timeout)
        extracted = file_ops.safe_extract_zip(zip_path, temp_dir)
        gltf_candidates = [path for path in extracted if path.endswith(".gltf") or path.endswith(".glb")]
        if not gltf_candidates:
            file_ops.cleanup_path(temp_dir)
            raise ValueError("No glTF file found in the downloaded model")
        return {"main_filepath": gltf_candidates[0], "temp_dir": temp_dir}

    def create_rodin_job(self, mode, api_key, text_prompt=None, images=None, bbox_condition=None):
        if mode == "MAIN_SITE":
            files = [
                *[("images", (f"{index:04d}{suffix}", image)) for index, (suffix, image) in enumerate(images or [])],
                ("tier", (None, "Sketch")),
                ("mesh_mode", (None, "Raw")),
            ]
            if text_prompt:
                files.append(("prompt", (None, text_prompt)))
            if bbox_condition:
                files.append(("bbox_condition", (None, json.dumps(bbox_condition))))
            response = self._request(
                "POST",
                "https://hyperhuman.deemos.com/api/v2/rodin",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                timeout=self.long_timeout,
                error_context="Hyper3D job creation",
            )
            return response.json()

        if mode == "FAL_AI":
            payload = {"tier": "Sketch"}
            if images:
                payload["input_image_urls"] = images
            if text_prompt:
                payload["prompt"] = text_prompt
            if bbox_condition:
                payload["bbox_condition"] = bbox_condition
            response = self._request(
                "POST",
                "https://queue.fal.run/fal-ai/hyper3d/rodin",
                headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.long_timeout,
                error_context="fal.ai Hyper3D job creation",
            )
            return response.json()

        raise ValueError("Unknown Hyper3D mode")

    def poll_rodin_job_status(self, mode, api_key, subscription_key=None, request_id=None):
        if mode == "MAIN_SITE":
            if not subscription_key:
                raise ValueError("subscription_key is required for MAIN_SITE mode")
            response = self._request(
                "POST",
                "https://hyperhuman.deemos.com/api/v2/status",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"subscription_key": subscription_key},
                timeout=self.default_timeout,
                error_context="Hyper3D status request",
            )
            data = response.json()
            return {"status_list": [item["status"] for item in data.get("jobs", [])]}

        if mode == "FAL_AI":
            if not request_id:
                raise ValueError("request_id is required for FAL_AI mode")
            response = self._request(
                "GET",
                f"https://queue.fal.run/fal-ai/hyper3d/requests/{request_id}/status",
                headers={"Authorization": f"Key {api_key}"},
                timeout=self.default_timeout,
                error_context="fal.ai Hyper3D status request",
            )
            return response.json()

        raise ValueError("Unknown Hyper3D mode")

    def download_rodin_asset(self, mode, api_key, task_uuid=None, request_id=None):
        if mode == "MAIN_SITE":
            if not task_uuid:
                raise ValueError("task_uuid is required for MAIN_SITE mode")
            response = self._request(
                "POST",
                "https://hyperhuman.deemos.com/api/v2/download",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"task_uuid": task_uuid},
                timeout=self.long_timeout,
                error_context="Hyper3D asset download request",
            )
            data = response.json()
            for item in data.get("list", []):
                if item["name"].endswith(".glb"):
                    temp_dir = file_ops.create_temp_dir("blendermcp_rodin_")
                    file_path = os.path.join(temp_dir, f"{task_uuid}.glb")
                    file_ops.download_to_file(item["url"], file_path, timeout=self.long_timeout)
                    return {"filepath": file_path, "temp_dir": temp_dir}
            raise ValueError("No GLB asset is available yet")

        if mode == "FAL_AI":
            if not request_id:
                raise ValueError("request_id is required for FAL_AI mode")
            response = self._request(
                "GET",
                f"https://queue.fal.run/fal-ai/hyper3d/requests/{request_id}",
                headers={"Authorization": f"Key {api_key}"},
                timeout=self.long_timeout,
                error_context="fal.ai Hyper3D asset request",
            )
            model_url = response.json().get("model_mesh", {}).get("url")
            if not model_url:
                raise ValueError("No model mesh URL is available yet")
            temp_dir = file_ops.create_temp_dir("blendermcp_fal_")
            file_path = os.path.join(temp_dir, f"{request_id}.glb")
            file_ops.download_to_file(model_url, file_path, timeout=self.long_timeout)
            return {"filepath": file_path, "temp_dir": temp_dir}

        raise ValueError("Unknown Hyper3D mode")

    def get_tencent_cloud_sign_headers(self, method, path, head_params, data, service, region, secret_id, secret_key, host=None):
        timestamp = int(datetime.utcnow().timestamp())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        host = host or f"{service}.tencentcloudapi.com"
        endpoint = f"https://{host}"
        payload = json.dumps(data)

        canonical_headers = (
            "content-type:application/json; charset=utf-8\n"
            f"host:{host}\n"
            f"x-tc-action:{head_params.get('Action', '').lower()}\n"
        )
        signed_headers = "content-type;host;x-tc-action"
        hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = "\n".join([method, path, "", canonical_headers, signed_headers, hashed_payload])
        credential_scope = f"{date}/{service}/tc3_request"
        string_to_sign = "\n".join(
            [
                "TC3-HMAC-SHA256",
                str(timestamp),
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

        def sign(key, message):
            return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()

        secret_date = sign(("TC3" + secret_key).encode("utf-8"), date)
        secret_service = sign(secret_date, service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization = (
            "TC3-HMAC-SHA256 "
            f"Credential={secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": head_params.get("Action", ""),
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": head_params.get("Version", ""),
            "X-TC-Region": region,
        }
        return headers, endpoint

    def create_hunyuan_job_official(self, secret_id, secret_key, text_prompt=None, image_data=None):
        if not text_prompt and not image_data:
            raise ValueError("Prompt or image is required")
        if text_prompt and image_data:
            raise ValueError("Prompt and image cannot be used together")

        service = "hunyuan"
        region = "ap-guangzhou"
        head_params = {"Action": "SubmitHunyuanTo3DJob", "Version": "2023-09-01", "Region": region}
        data = {"Num": 1}
        if text_prompt:
            if len(text_prompt) > 200:
                raise ValueError("Prompt exceeds 200 characters")
            data["Prompt"] = text_prompt
        if image_data:
            if image_data.startswith(("http://", "https://")):
                data["ImageUrl"] = image_data
            else:
                with open(image_data, "rb") as handle:
                    data["ImageBase64"] = base64.b64encode(handle.read()).decode("ascii")

        headers, endpoint = self.get_tencent_cloud_sign_headers("POST", "/", head_params, data, service, region, secret_id, secret_key)
        response = self._request(
            "POST",
            endpoint,
            headers=headers,
            data=json.dumps(data),
            timeout=self.long_timeout,
            error_context="Hunyuan official job creation",
        )
        return response.json()

    def create_hunyuan_job_local(self, base_url, text_prompt=None, image_data=None, octree_resolution=256, num_inference_steps=20, guidance_scale=5.5, texture=False):
        if not text_prompt and not image_data:
            raise ValueError("Prompt or image is required")

        payload = {
            "octree_resolution": octree_resolution,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "texture": texture,
        }
        if text_prompt:
            payload["text"] = text_prompt
        if image_data:
            if re.match(r"^https?://", image_data, re.IGNORECASE):
                image_response = self._request(
                    "GET",
                    image_data,
                    timeout=self.default_timeout,
                    error_context="Hunyuan local image fetch",
                )
                payload["image"] = base64.b64encode(image_response.content).decode("ascii")
            else:
                with open(image_data, "rb") as handle:
                    payload["image"] = base64.b64encode(handle.read()).decode("ascii")

        response = self._request(
            "POST",
            f"{base_url.rstrip('/')}/generate",
            json=payload,
            timeout=self.generation_timeout,
            error_context="Hunyuan local generation",
        )
        temp_dir = file_ops.create_temp_dir("blendermcp_hunyuan_local_")
        file_path = os.path.join(temp_dir, "generated.glb")
        with open(file_path, "wb") as handle:
            handle.write(response.content)
        return {"filepath": file_path, "temp_dir": temp_dir}

    def poll_hunyuan_job_status(self, secret_id, secret_key, job_id):
        service = "hunyuan"
        region = "ap-guangzhou"
        head_params = {"Action": "QueryHunyuanTo3DJob", "Version": "2023-09-01", "Region": region}
        data = {"JobId": job_id.removeprefix("job_")}
        headers, endpoint = self.get_tencent_cloud_sign_headers("POST", "/", head_params, data, service, region, secret_id, secret_key)
        response = self._request(
            "POST",
            endpoint,
            headers=headers,
            data=json.dumps(data),
            timeout=self.long_timeout,
            error_context="Hunyuan status request",
        )
        return response.json()

    def download_hunyuan_zip(self, zip_file_url):
        temp_dir = file_ops.create_temp_dir("blendermcp_hunyuan_zip_")
        zip_path = os.path.join(temp_dir, "model.zip")
        file_ops.download_to_file(zip_file_url, zip_path, timeout=self.long_timeout)
        extracted = file_ops.safe_extract_zip(zip_path, temp_dir)
        obj_candidates = [path for path in extracted if path.lower().endswith(".obj")]
        if not obj_candidates:
            file_ops.cleanup_path(temp_dir)
            raise ValueError("OBJ file not found after extraction")
        return {"filepath": obj_candidates[0], "temp_dir": temp_dir}
