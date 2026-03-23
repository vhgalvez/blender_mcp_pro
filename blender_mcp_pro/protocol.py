import codecs
import json

from .tool_registry import COMMAND_SCHEMAS

MAX_MESSAGE_SIZE = 1024 * 1024


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


def make_jsonrpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_jsonrpc_error(request_id, code, message, data=None):
    payload = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    return payload


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

        if message.get("jsonrpc") == "2.0":
            return self._parse_jsonrpc_message(message)

        request_id = message.get("id")
        if request_id is None:
            raise ProtocolError("missing_request_id", "Message must include an id")
        if isinstance(request_id, str):
            if not request_id.strip():
                raise ProtocolError("missing_request_id", "Message must include a non-empty string id")
            if len(request_id.encode("utf-8")) > 128:
                raise ProtocolError("invalid_request_id", "Request id exceeds the maximum size", request_id=request_id)
            request_id = request_id.strip()
        elif not isinstance(request_id, (int, float)):
            raise ProtocolError("invalid_request_id", "Message id must be a string or number")
        message["id"] = request_id

        message_type = message.get("type")

        if message_type == "auth":
            return self._parse_auth_message(message)
        if message_type == "command":
            return self._parse_command_message(message)
        if isinstance(message_type, str) and message_type:
            return self._parse_legacy_direct_command(message)
        raise ProtocolError("invalid_type", "Message type must be 'auth', 'command', or a legacy command name", request_id=request_id)

    def _parse_auth_message(self, message):
        request_id = message["id"]
        allowed_keys = {"id", "type", "token"}
        extra_keys = set(message.keys()) - allowed_keys
        if extra_keys:
            raise ProtocolError("invalid_auth", f"Auth message contains unsupported fields: {sorted(extra_keys)}", request_id=request_id)
        token = message.get("token")
        if not isinstance(token, str) or not token:
            raise ProtocolError("invalid_auth", "Auth message requires a non-empty token", request_id=request_id)
        message["kind"] = "auth"
        return message

    def _parse_command_message(self, message):
        request_id = message["id"]
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
        message["kind"] = "legacy_command"
        return message

    def _parse_legacy_direct_command(self, message):
        request_id = message["id"]
        command = message["type"]
        params = message.get("params")
        if params is None:
            params = {key: value for key, value in message.items() if key not in {"id", "type"}}
        if not isinstance(params, dict):
            raise ProtocolError("invalid_params", "params must be an object", request_id=request_id)
        return {
            "id": request_id,
            "kind": "legacy_direct_command",
            "command": command,
            "params": params,
        }

    def _parse_jsonrpc_message(self, message):
        request_id = message.get("id")
        if isinstance(request_id, str):
            if not request_id.strip():
                raise ProtocolError("invalid_request_id", "JSON-RPC string ids cannot be empty")
            if len(request_id.encode("utf-8")) > 128:
                raise ProtocolError("invalid_request_id", "Request id exceeds the maximum size", request_id=request_id)
            request_id = request_id.strip()
        elif request_id is not None and not isinstance(request_id, (int, float)):
            raise ProtocolError("invalid_request_id", "JSON-RPC id must be a string, number, or null")
        method = message.get("method")
        if not isinstance(method, str) or not method:
            raise ProtocolError("invalid_method", "JSON-RPC message requires a non-empty method", request_id=request_id)
        params = message.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ProtocolError("invalid_params", "JSON-RPC params must be an object", request_id=request_id)
        return {
            "id": request_id,
            "kind": "jsonrpc",
            "method": method,
            "params": params,
        }
