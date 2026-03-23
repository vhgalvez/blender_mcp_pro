import json
import socket
from typing import Any


HOST = "127.0.0.1"
PORT = 9876
TOKEN = "123456"
TIMEOUT_SECONDS = 5


def recv_line(sock: socket.socket) -> str:
    buffer = b""
    while not buffer.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk
    return buffer.decode("utf-8").strip()


def send_line(sock: socket.socket, msg: dict[str, Any]) -> None:
    sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))


def parse_json_line(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Respuesta JSON inválida: {raw}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"La respuesta no es un objeto JSON: {raw}")

    return data


def raise_if_not_ok(response: dict[str, Any], prefix: str) -> None:
    if response.get("ok", False):
        return

    error = response.get("error", {})
    code = error.get("code", "unknown_error")
    message = error.get("message", "Error desconocido")
    raise RuntimeError(f"{prefix} [{code}]: {message}")


def send_command(command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if params is None:
        params = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(TIMEOUT_SECONDS)
        s.connect((HOST, PORT))

        auth_msg = {
            "id": "auth-1",
            "type": "auth",
            "token": TOKEN,
        }
        send_line(s, auth_msg)

        auth_raw = recv_line(s)
        print("AUTH:", auth_raw)
        if not auth_raw:
            raise RuntimeError(
                "El servidor cerró la conexión sin responder al auth.")

        auth_response = parse_json_line(auth_raw)
        raise_if_not_ok(auth_response, "Auth falló")

        cmd_msg = {
            "id": "cmd-1",
            "type": "command",
            "command": command,
            "params": params,
        }
        send_line(s, cmd_msg)

        result_raw = recv_line(s)
        print("RESULT:", result_raw)
        if not result_raw:
            raise RuntimeError(
                "El servidor cerró la conexión sin responder al comando.")

        result_response = parse_json_line(result_raw)
        raise_if_not_ok(result_response, "Comando falló")

        return result_response


if __name__ == "__main__":
    response = send_command(
        "create_prop_blockout",
        {
            "prop_type": "chair",
            "mode": "create",
        },
    )
    print("OK:", json.dumps(response, indent=2, ensure_ascii=False))
