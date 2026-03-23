import socket
import json

HOST = "127.0.0.1"
PORT = 9876
TOKEN = "123456"

def recv_line(sock):
    buffer = b""
    while not buffer.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk
    return buffer.decode("utf-8").strip()

def send_line(sock, msg):
    sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))

def send_command(command, params=None):
    if params is None:
        params = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        # AUTH
        send_line(s, {
            "id": 1,
            "type": "auth",
            "token": TOKEN
        })
        auth_response = recv_line(s)
        print("AUTH:", auth_response)

        # COMMAND
        send_line(s, {
            "id": 2,
            "type": "command",
            "command": command,
            "params": params
        })
        result_response = recv_line(s)
        print("RESULT:", result_response)

if __name__ == "__main__":
    send_command("create_prop_blockout", {"type": "chair"})