import codecs
import json


MAX_MESSAGE_SIZE = 1024 * 1024

COMMAND_SCHEMAS = {
    "get_scene_info": {"params": {}},
    "get_object_info": {"params": {"name": str}, "required": {"name"}},
    "get_viewport_screenshot": {"params": {"filepath": str, "format": str, "max_size": int}},
    "get_telemetry_consent": {"params": {}},
    "get_polyhaven_status": {"params": {}},
    "get_hyper3d_status": {"params": {}},
    "get_sketchfab_status": {"params": {}},
    "get_hunyuan3d_status": {"params": {}},
    "get_polyhaven_categories": {"params": {"asset_type": str}, "required": {"asset_type"}},
    "search_polyhaven_assets": {"params": {"asset_type": str, "categories": str}},
    "download_polyhaven_asset": {"params": {"asset_id": str, "asset_type": str, "resolution": str, "file_format": str}, "required": {"asset_id", "asset_type"}},
    "set_texture": {"params": {"object_name": str, "texture_id": str}, "required": {"object_name", "texture_id"}},
    "create_rodin_job": {"params": {"text_prompt": str, "images": list, "bbox_condition": dict}},
    "poll_rodin_job_status": {"params": {"subscription_key": str, "request_id": str}},
    "import_generated_asset": {"params": {"task_uuid": str, "request_id": str, "name": str}, "required": {"name"}},
    "search_sketchfab_models": {"params": {"query": str, "categories": str, "count": int, "downloadable": bool}, "required": {"query"}},
    "get_sketchfab_model_preview": {"params": {"uid": str}, "required": {"uid"}},
    "download_sketchfab_model": {"params": {"uid": str, "normalize_size": bool, "target_size": float}, "required": {"uid"}},
    "create_hunyuan_job": {"params": {"text_prompt": str, "image": str}},
    "poll_hunyuan_job_status": {"params": {"job_id": str}, "required": {"job_id"}},
    "import_generated_asset_hunyuan": {"params": {"name": str, "zip_file_url": str}, "required": {"name", "zip_file_url"}},
    "load_character_references": {"params": {"mode": str, "front": str, "side": str, "back": str}, "required": {"front", "side"}},
    "clear_character_references": {"params": {"mode": str}},
    "create_character_blockout": {"params": {"mode": str, "height": float, "collection_name": str}},
    "apply_character_symmetry": {"params": {"mode": str, "object_names": list, "use_bisect": bool, "use_clip": bool}},
    "build_character_hair": {"params": {"mode": str, "spike_count": int, "collection_name": str}},
    "build_character_face": {"params": {"mode": str, "add_piercings": bool, "collection_name": str}},
    "apply_character_materials": {"params": {"mode": str, "include_metal": bool}},
    "capture_character_review": {"params": {"mode": str}},
    "compare_character_with_references": {"params": {"mode": str}},
    "apply_character_proportion_fixes": {"params": {"mode": str, "correction_report": dict, "deltas": dict, "strength": float}},
    "create_prop_blockout": {"params": {"mode": str, "prop_type": str, "collection_name": str}, "required": {"mode", "prop_type"}},
    "apply_prop_symmetry": {"params": {"mode": str, "object_names": list, "use_bisect": bool, "use_clip": bool}, "required": {"mode"}},
    "apply_prop_materials": {"params": {"mode": str, "include_metal": bool}, "required": {"mode"}},
    "create_environment_layout": {"params": {"mode": str, "layout_type": str, "collection_name": str}, "required": {"mode", "layout_type"}},
    "apply_environment_materials": {"params": {"mode": str}, "required": {"mode"}},
}


class ProtocolError(Exception):
    def __init__(self, code, message, request_id=None, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.details = details

def make_error(request_id, code, message, details=None):
    payload = {"id": request_id, "ok": False, "error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


def make_result(request_id, result):
    return {"id": request_id, "ok": True, "result": result}


def encode_message(payload):
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


class NDJSONProtocol:
    def __init__(self, max_message_size=MAX_MESSAGE_SIZE):
        self.max_message_size = max_message_size
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        self._buffer = ""

    def feed_data(self, data):
        try:
            self._buffer += self._decoder.decode(data)
        except UnicodeDecodeError as exc:
            raise ProtocolError("invalid_encoding", "Message must be valid UTF-8") from exc
        if len(self._buffer.encode("utf-8")) > self.max_message_size:
            raise ProtocolError("message_too_large", "Buffered message exceeds the maximum size")

        messages = []
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            if len(line.encode("utf-8")) > self.max_message_size:
                raise ProtocolError("message_too_large", "Message exceeds the maximum size")
            messages.append(self.parse_line(line))
        return messages

    def parse_line(self, line):
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProtocolError("invalid_json", f"Invalid JSON: {exc.msg}") from exc

        if not isinstance(message, dict):
            raise ProtocolError("invalid_message", "Message must be a JSON object")

        request_id = message.get("id")
        if not isinstance(request_id, str) or not request_id.strip():
            raise ProtocolError("missing_request_id", "Message must include a non-empty string id")
        if len(request_id.encode("utf-8")) > 128:
            raise ProtocolError("invalid_request_id", "Request id exceeds the maximum size", request_id=request_id)
        request_id = request_id.strip()
        message["id"] = request_id
        message_type = message.get("type")

        if message_type not in {"auth", "command"}:
            raise ProtocolError("invalid_type", "Message type must be 'auth' or 'command'", request_id=request_id)

        if message_type == "auth":
            allowed_keys = {"id", "type", "token"}
            extra_keys = set(message.keys()) - allowed_keys
            if extra_keys:
                raise ProtocolError("invalid_auth", f"Auth message contains unsupported fields: {sorted(extra_keys)}", request_id=request_id)
            token = message.get("token")
            if not isinstance(token, str) or not token:
                raise ProtocolError("invalid_auth", "Auth message requires a non-empty token", request_id=request_id)
        else:
            allowed_keys = {"id", "type", "command", "params"}
            extra_keys = set(message.keys()) - allowed_keys
            if extra_keys:
                raise ProtocolError("invalid_command", f"Command message contains unsupported fields: {sorted(extra_keys)}", request_id=request_id)
            command = message.get("command")
            if not isinstance(command, str) or not command:
                raise ProtocolError("invalid_command", "Command message requires a non-empty command", request_id=request_id)
            params = message.get("params", {})
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise ProtocolError("invalid_params", "params must be an object", request_id=request_id)
            message["params"] = params

        return message
