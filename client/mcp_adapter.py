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

        return s.recv(4096).decode()


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle_message(msg):
    msg_type = msg.get("type")

    # 🔹 MCP handshake
    if msg_type == "initialize":
        send({
            "type": "initialize",
            "result": {
                "name": "blender-mcp",
                "version": "1.0"
            }
        })

    # 🔹 declarar tools
    elif msg_type == "tools/list":
        send({
            "type": "tools/list",
            "result": [
                {
                    "name": "create_chair",
                    "description": "Create a chair in Blender",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        })

    # 🔹 ejecutar tool
    elif msg_type == "tools/call":
        name = msg["name"]

        if name == "create_chair":
            result = send_to_blender("create_prop_blockout", {
                "prop_type": "chair",
                "mode": "props"
            })

            send({
                "type": "tools/call",
                "result": result
            })

        else:
            send({
                "type": "error",
                "message": "Unknown tool"
            })


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break

        try:
            msg = json.loads(line)
            handle_message(msg)
        except Exception as e:
            send({
                "type": "error",
                "message": str(e)
            })


if __name__ == "__main__":
    main()