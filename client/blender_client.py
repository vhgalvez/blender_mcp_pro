import json
import logging
import os
import socket
import uuid
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT_SECONDS = 10.0

LOGGER = logging.getLogger("blender_mcp_bridge.client")


class BlenderClientError(RuntimeError):
    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


class BlenderTcpClient:
    def __init__(self, host: str, port: int, token: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
        self.host = host
        self.port = port
        self.token = token
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "BlenderTcpClient":
        host = os.environ.get("BLENDER_HOST", DEFAULT_HOST)
        raw_port = os.environ.get("BLENDER_PORT", str(DEFAULT_PORT))
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise RuntimeError(f"BLENDER_PORT must be an integer, got: {raw_port!r}") from exc
        token = os.environ.get("BLENDER_TOKEN", "")
        return cls(host=host, port=port, token=token)

    def call(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("BLENDER_TOKEN is required")
        if params is None:
            params = {}

        LOGGER.info("Connecting to Blender backend %s:%s for command=%s", self.host, self.port, command)
        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as sock:
            sock.settimeout(self.timeout_seconds)
            self._send_message(
                sock,
                {
                    "id": f"auth-{uuid.uuid4().hex}",
                    "type": "auth",
                    "token": self.token,
                },
            )
            auth_response = self._read_message(sock)
            self._raise_if_not_ok(auth_response, "Authentication with Blender failed")

            self._send_message(
                sock,
                {
                    "id": f"cmd-{uuid.uuid4().hex}",
                    "type": "command",
                    "command": command,
                    "params": params,
                },
            )
            response = self._read_message(sock)
            self._raise_if_not_ok(response, f"Blender command failed: {command}")
            if "result" not in response:
                raise RuntimeError(f"Blender backend returned ok=true without result for command: {command}")
            LOGGER.info("Blender backend command succeeded command=%s", command)
            return response["result"]

    def _send_message(self, sock: socket.socket, payload: dict[str, Any]) -> None:
        sock.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))

    def _read_message(self, sock: socket.socket) -> dict[str, Any]:
        buffer = b""
        while not buffer.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            buffer += chunk
        if not buffer:
            raise RuntimeError("Blender server closed the connection without responding")

        try:
            message = json.loads(buffer.decode("utf-8").strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError("Blender server returned invalid JSON") from exc
        if not isinstance(message, dict):
            raise RuntimeError("Blender server returned a non-object JSON payload")
        return message

    def _raise_if_not_ok(self, response: dict[str, Any], prefix: str) -> None:
        if response.get("ok"):
            return
        error = response.get("error", {})
        code = error.get("code", "unknown_error")
        message = error.get("message", prefix)
        details = error.get("details")
        LOGGER.warning("Blender backend error code=%s message=%s", code, message)
        raise BlenderClientError(code=code, message=f"{prefix}: {message}", details=details)


if __name__ == "__main__":
    result = BlenderTcpClient.from_env().call("get_scene_info")
    print(json.dumps(result, indent=2, ensure_ascii=False))
