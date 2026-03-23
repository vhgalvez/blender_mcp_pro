import json
import logging
import os
import socket
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


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
    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.host = host
        self.port = port
        self.token = token
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "BlenderTcpClient":
        """
        Carga variables desde el archivo .env ubicado en el mismo directorio
        que este archivo, y luego construye el cliente.
        """
        env_path = Path(__file__).resolve().parent / ".env"
        load_dotenv(env_path)

        host = os.getenv("BLENDER_HOST", DEFAULT_HOST)
        raw_port = os.getenv("BLENDER_PORT", str(DEFAULT_PORT))
        raw_timeout = os.getenv("BLENDER_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        token = os.getenv("BLENDER_TOKEN", "").strip()

        try:
            port = int(raw_port)
        except ValueError as exc:
            raise RuntimeError(f"BLENDER_PORT must be an integer, got: {raw_port!r}") from exc

        try:
            timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise RuntimeError(
                f"BLENDER_TIMEOUT_SECONDS must be a number, got: {raw_timeout!r}"
            ) from exc

        if timeout_seconds <= 0:
            raise RuntimeError("BLENDER_TIMEOUT_SECONDS must be greater than zero")

        return cls(
            host=host,
            port=port,
            token=token,
            timeout_seconds=timeout_seconds,
        )

    def call(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("BLENDER_TOKEN is required")

        if params is None:
            params = {}

        auth_request_id = f"auth-{uuid.uuid4().hex}"
        command_request_id = f"cmd-{uuid.uuid4().hex}"

        LOGGER.info(
            "Connecting to Blender backend host=%s port=%s timeout=%ss command=%s request_id=%s",
            self.host,
            self.port,
            self.timeout_seconds,
            command,
            command_request_id,
        )

        try:
            sock = socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout_seconds,
            )
        except OSError as exc:
            LOGGER.error(
                "Backend connection failed host=%s port=%s command=%s request_id=%s error=%s",
                self.host,
                self.port,
                command,
                command_request_id,
                exc,
            )
            raise RuntimeError(
                f"Could not connect to Blender backend at {self.host}:{self.port}. "
                "Start the Blender add-on server and confirm BLENDER_HOST/BLENDER_PORT."
            ) from exc

        with sock:
            sock.settimeout(self.timeout_seconds)

            self._send_message(
                sock,
                {
                    "id": auth_request_id,
                    "type": "auth",
                    "token": self.token,
                },
            )
            auth_response = self._read_message(sock)
            self._raise_if_not_ok(auth_response, "Authentication with Blender failed")
            LOGGER.info(
                "Backend authentication succeeded host=%s port=%s request_id=%s",
                self.host,
                self.port,
                auth_request_id,
            )

            self._send_message(
                sock,
                {
                    "id": command_request_id,
                    "type": "command",
                    "command": command,
                    "params": params,
                },
            )
            response = self._read_message(sock)
            self._raise_if_not_ok(response, f"Blender command failed: {command}")

            if "result" not in response:
                LOGGER.error(
                    "Backend command returned ok without result command=%s request_id=%s",
                    command,
                    command_request_id,
                )
                raise RuntimeError(
                    f"Blender backend returned ok=true without result for command: {command}"
                )

            LOGGER.info(
                "Blender backend command succeeded command=%s request_id=%s",
                command,
                command_request_id,
            )
            return response["result"]

    def _send_message(self, sock: socket.socket, payload: dict[str, Any]) -> None:
        data = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        sock.sendall(data)

    def _read_message(self, sock: socket.socket) -> dict[str, Any]:
        buffer = b""

        while not buffer.endswith(b"\n"):
            try:
                chunk = sock.recv(4096)
            except socket.timeout as exc:
                raise RuntimeError(
                    f"Timed out waiting for Blender backend response from {self.host}:{self.port}"
                ) from exc

            if not chunk:
                break

            buffer += chunk

        if not buffer:
            raise RuntimeError(
                f"Blender backend at {self.host}:{self.port} closed the connection without responding"
            )

        try:
            message = json.loads(buffer.decode("utf-8").strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Blender backend at {self.host}:{self.port} returned invalid JSON"
            ) from exc

        if not isinstance(message, dict):
            raise RuntimeError(
                f"Blender backend at {self.host}:{self.port} returned a non-object JSON payload"
            )

        return message

    def _raise_if_not_ok(self, response: dict[str, Any], prefix: str) -> None:
        if response.get("ok"):
            return

        error = response.get("error", {})
        code = error.get("code", "unknown_error")
        message = error.get("message", prefix)
        details = error.get("details")

        LOGGER.warning(
            "Blender backend error code=%s message=%s response_id=%s",
            code,
            message,
            response.get("id"),
        )
        raise BlenderClientError(
            code=code,
            message=f"{prefix}: {message}",
            details=details,
        )


if __name__ == "__main__":
    result = BlenderTcpClient.from_env().call("get_scene_info")
    print(json.dumps(result, indent=2, ensure_ascii=False))
