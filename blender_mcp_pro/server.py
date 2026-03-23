import hmac
import json
import ipaddress
import logging
import socket
import threading
import traceback

import bpy

from .dispatcher import CommandDispatcher
from . import file_ops
from .protocol import (
    NDJSONProtocol,
    ProtocolError,
    encode_message,
    make_error,
    make_jsonrpc_error,
    make_jsonrpc_result,
    make_result,
)
from .tool_registry import build_mcp_tool_definition, get_backend_tool, iter_backend_tools


class BlenderMCPServer:
    def __init__(self, host="127.0.0.1", port=9876, addon_module_name="addon"):
        self.host = host
        self.port = port
        self.addon_module_name = addon_module_name
        self.running = False
        self.socket = None
        self.server_thread = None
        self.dispatcher = CommandDispatcher(addon_module_name, self.call_in_main_thread)
        self.audit_logger = self._build_audit_logger()

    def start(self):
        if self.running:
            return

        token = self._get_auth_token()
        if not token:
            raise RuntimeError("Auth token is required before starting the server")
        self._validate_network_settings()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(8)
        self.socket.settimeout(1.0)

        self.running = True
        self.server_thread = threading.Thread(target=self._server_loop, name="BlenderMCPServer", daemon=True)
        self.server_thread.start()
        self.audit_logger.info("server_started host=%s port=%s mode=%s", self.host, self.port, self._connection_mode())

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
        self.server_thread = None
        self.audit_logger.info("server_stopped host=%s port=%s mode=%s", self.host, self.port, self._connection_mode())

    def _server_loop(self):
        while self.running:
            try:
                client, address = self.socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            validation_mode = self._connection_mode()
            if not self._is_client_allowed(address[0]):
                self.audit_logger.warning(
                    "client_rejected address=%s port=%s mode=%s reason=ip_not_allowed",
                    address[0],
                    address[1],
                    validation_mode,
                )
                try:
                    client.sendall(encode_message(make_error(None, "ip_not_allowed", "Client IP is not allowed by the current server mode")))
                except Exception:
                    pass
                client.close()
                continue
            self.audit_logger.info("client_accepted address=%s port=%s mode=%s", address[0], address[1], validation_mode)
            thread = threading.Thread(target=self._handle_client, args=(client, address), daemon=True)
            thread.start()

    def _handle_client(self, client, address):
        protocol = NDJSONProtocol()
        authenticated = False
        client.settimeout(5.0)
        validation_mode = self._connection_mode()

        try:
            while self.running:
                try:
                    data = client.recv(8192)
                except socket.timeout:
                    continue

                if not data:
                    break

                try:
                    messages = protocol.feed_data(data)
                except ProtocolError as exc:
                    self.audit_logger.warning(
                        "client_rejected address=%s port=%s mode=%s reason=%s",
                        address[0],
                        address[1],
                        validation_mode,
                        exc.code,
                    )
                    client.sendall(encode_message(make_error(exc.request_id, exc.code, exc.message, exc.details)))
                    break

                for message in messages:
                    request_id = message.get("id")
                    try:
                        if not authenticated:
                            if message["kind"] != "auth":
                                raise ProtocolError("not_authenticated", "Authenticate before sending commands", request_id=request_id)
                            if not self._authenticate(message["token"]):
                                self.audit_logger.warning(
                                    "client_rejected address=%s port=%s mode=%s reason=auth_failed",
                                    address[0],
                                    address[1],
                                    validation_mode,
                                )
                                raise ProtocolError("auth_failed", "Authentication failed", request_id=request_id)
                            authenticated = True
                            self.audit_logger.info(
                                "client_authenticated address=%s port=%s mode=%s request_id=%s",
                                address[0],
                                address[1],
                                validation_mode,
                                request_id,
                            )
                            client.sendall(encode_message(make_result(request_id, {"authenticated": True, "host": self.host, "port": self.port})))
                            continue

                        response = self._handle_authenticated_message(message)
                        if response is not None:
                            client.sendall(encode_message(response))
                    except ProtocolError as exc:
                        self.audit_logger.warning(
                            "client_rejected address=%s port=%s mode=%s request_id=%s reason=%s",
                            address[0],
                            address[1],
                            validation_mode,
                            request_id,
                            exc.code,
                        )
                        if message.get("kind") == "jsonrpc":
                            client.sendall(encode_message(make_jsonrpc_error(exc.request_id if exc.request_id is not None else request_id, -32602, exc.message, exc.details)))
                        else:
                            client.sendall(encode_message(make_error(exc.request_id or request_id, exc.code, exc.message, exc.details)))
                    except Exception as exc:
                        traceback.print_exc()
                        self.audit_logger.exception(
                            "client_error address=%s port=%s mode=%s request_id=%s",
                            address[0],
                            address[1],
                            validation_mode,
                            request_id,
                        )
                        if message.get("kind") == "jsonrpc":
                            client.sendall(encode_message(make_jsonrpc_error(request_id, -32603, str(exc))))
                        else:
                            client.sendall(encode_message(make_error(request_id, "internal_error", str(exc))))
        finally:
            try:
                client.close()
            except Exception:
                pass
            self.audit_logger.info("client_disconnected address=%s port=%s mode=%s", address[0], address[1], validation_mode)

    def _handle_authenticated_message(self, message):
        request_id = message["id"]
        kind = message["kind"]

        if kind in {"legacy_command", "legacy_direct_command"}:
            result = self.dispatcher.dispatch(message["command"], message["params"])
            return make_result(request_id, result)

        if kind != "jsonrpc":
            raise ProtocolError("invalid_type", "Unsupported message kind after authentication", request_id=request_id)

        method = message["method"]
        params = message["params"]

        if method == "initialize":
            return make_jsonrpc_result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "blender-mcp-pro-tcp", "version": "1.0.0"},
                },
            )

        if method == "ping":
            return make_jsonrpc_result(request_id, {})

        if method == "tools/list":
            tools = [
                build_mcp_tool_definition(tool)
                for tool in iter_backend_tools(exposed_only=True)
                if hasattr(self.dispatcher, f"cmd_{tool['command']}")
            ]
            return make_jsonrpc_result(request_id, {"tools": tools})

        if method == "tools/call":
            requested_name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(requested_name, str) or not requested_name:
                return make_jsonrpc_result(
                    request_id,
                    self._mcp_tool_error("missing_tool_name", "Tool name is required."),
                )
            if not isinstance(arguments, dict):
                return make_jsonrpc_result(
                    request_id,
                    self._mcp_tool_error("invalid_arguments", "Tool arguments must be an object."),
                )

            tool = get_backend_tool(requested_name)
            if tool is None or not hasattr(self.dispatcher, f"cmd_{tool['command']}"):
                return make_jsonrpc_result(
                    request_id,
                    self._mcp_tool_error("unknown_tool", f"Unknown tool: {requested_name}"),
                )

            result = self.dispatcher.dispatch(tool["command"], arguments)
            return make_jsonrpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "structuredContent": result,
                    "isError": False,
                },
            )

        if method == "notifications/initialized":
            return None

        if method in {"shutdown", "exit"}:
            return make_jsonrpc_result(request_id, {})

        return make_jsonrpc_error(request_id, -32601, f"Method not found: {method}")

    def _mcp_tool_error(self, code, message):
        payload = {"error": code, "message": message}
        return {
            "content": [{"type": "text", "text": message}],
            "structuredContent": payload,
            "isError": True,
        }

    def _authenticate(self, token):
        expected = self._get_auth_token()
        return bool(expected) and hmac.compare_digest(token, expected)

    def _get_auth_token(self):
        def read():
            addon = bpy.context.preferences.addons.get(self.addon_module_name)
            if not addon:
                return ""
            return addon.preferences.auth_token

        return self.call_in_main_thread(read)

    def _get_network_settings(self):
        def read():
            addon = bpy.context.preferences.addons.get(self.addon_module_name)
            if not addon:
                return {
                    "local_only_mode": True,
                    "lan_mode_enabled": False,
                    "allowed_ips": "",
                    "allowed_subnets": "",
                }
            prefs = addon.preferences
            return {
                "local_only_mode": bool(prefs.local_only_mode),
                "lan_mode_enabled": bool(prefs.lan_mode_enabled),
                "allowed_ips": prefs.allowed_ips,
                "allowed_subnets": prefs.allowed_subnets,
            }

        return self.call_in_main_thread(read)

    def _connection_mode(self):
        settings = self._get_network_settings()
        return "lan_whitelist" if settings["lan_mode_enabled"] else "local_only"

    def _validate_network_settings(self):
        settings = self._get_network_settings()
        if settings["lan_mode_enabled"]:
            if not (settings["allowed_ips"].strip() or settings["allowed_subnets"].strip()):
                raise RuntimeError("LAN whitelist mode requires at least one allowed IP or subnet")
            self._parse_allowed_entries(settings["allowed_ips"], settings["allowed_subnets"])

    def _parse_allowed_entries(self, raw_ips, raw_subnets):
        ip_entries = []
        subnet_entries = []
        if raw_ips.strip():
            for token in [part.strip() for part in raw_ips.split(",") if part.strip()]:
                ip_entries.append(ipaddress.ip_address(token))
        if raw_subnets.strip():
            for token in [part.strip() for part in raw_subnets.split(",") if part.strip()]:
                subnet_entries.append(ipaddress.ip_network(token, strict=False))
        return ip_entries, subnet_entries

    def _is_client_allowed(self, client_ip):
        settings = self._get_network_settings()
        if not settings["lan_mode_enabled"]:
            return client_ip in {"127.0.0.1", "::1"}

        try:
            address = ipaddress.ip_address(client_ip)
            allowed_ips, allowed_subnets = self._parse_allowed_entries(settings["allowed_ips"], settings["allowed_subnets"])
            if any(address == allowed for allowed in allowed_ips):
                return True
            if any(address in subnet for subnet in allowed_subnets):
                return True
            return False
        except ValueError:
            return False

    def call_in_main_thread(self, func, timeout=30.0):
        if threading.current_thread() is threading.main_thread():
            return func()

        result = {}
        done = threading.Event()

        def wrapper():
            try:
                result["value"] = func()
            except Exception as exc:
                result["error"] = exc
            finally:
                done.set()
            return None

        bpy.app.timers.register(wrapper, first_interval=0.0)
        if not done.wait(timeout):
            raise TimeoutError("Timed out waiting for Blender main thread")
        if "error" in result:
            raise result["error"]
        return result.get("value")

    def _build_audit_logger(self):
        file_ops.ensure_runtime_dirs()
        logger = logging.getLogger(f"blendermcp.audit.{self.port}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            handler = logging.FileHandler(str(file_ops.SAFE_BASE_DIR / "audit.log"), encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        return logger
