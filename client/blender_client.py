import json
import socket
from typing import Any


HOST = "127.0.0.1"
PORT = 9876
TOKEN = "123456"


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
        if not isinstance(data, dict):
            raise ValueError("La respuesta no es un objeto JSON")
        return data
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Respuesta JSON inválida: {raw}") from exc


def send_command(command: str, params: dict[str, Any] | None = None) -> None:
    if params is None:
        params = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        auth_msg = {
            "id": "auth-1",
            "type": "auth",
            "token": TOKEN
        }
        send_line(s, auth_msg)

        auth_raw = recv_line(s)
        print("AUTH:", auth_raw)

        if not auth_raw:
            raise RuntimeError("El servidor cerró la conexión sin responder al auth.")

        auth_response = parse_json_line(auth_raw)
        if not auth_response.get("ok", False):
            error = auth_response.get("error", {})
            code = error.get("code", "unknown_error")
            message = error.get("message", "Error de autenticación desconocido")
            raise RuntimeError(f"Auth falló [{code}]: {message}")

        cmd_msg = {
            "id": "cmd-1",
            "type": "command",
            "command": command,
            "params": params
        }
        send_line(s, cmd_msg)

        result_raw = recv_line(s)
        print("RESULT:", result_raw)

        if not result_raw:
            raise RuntimeError("El servidor cerró la conexión sin responder al comando.")

        result_response = parse_json_line(result_raw)

        if not result_response.get("ok", False):
            error = result_response.get("error", {})
            code = error.get("code", "unknown_error")
            message = error.get("message", "Error de comando desconocido")
            raise RuntimeError(f"Comando falló [{code}]: {message}")


if __name__ == "__main__":
    send_command("create_prop_blockout")