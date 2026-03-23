import sys
import json
import socket

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "123456"


def send_to_blender(command, params):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        # AUTH
        s.send((json.dumps({
            "id": "auth-1",
            "type": "auth",
            "token": TOKEN
        }) + "\n").encode())

        s.recv(4096)

        # COMMAND
        s.send((json.dumps({
            "id": "cmd-1",
            "type": "command",
            "command": command,
            "params": params
        }) + "\n").encode())

        response = s.recv(4096).decode()
        return response


def handle_request(req):
    name = req.get("name")
    args = req.get("arguments", {})

    if name == "create_chair":
        return send_to_blender("create_prop_blockout", {
            "prop_type": "chair",
            "mode": "props"
        })

    return json.dumps({"error": "unknown tool"})


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break

        req = json.loads(line)

        result = handle_request(req)

        sys.stdout.write(result + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()