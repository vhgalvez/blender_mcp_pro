import os
import secrets

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from . import server as blendermcp_server


bl_info = {
    "name": "Blender MCP",
    "author": "BlenderMCP",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "Connect Blender to local MCP clients with authenticated commands",
    "category": "Interface",
}

ADDON_MODULE_NAME = __package__ or __name__.split(".")[0]


def get_addon_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(ADDON_MODULE_NAME)
    return addon.preferences if addon else None


def build_network_config(prefs):
    lan_enabled = bool(prefs and prefs.lan_mode_enabled)
    return {
        "host": "0.0.0.0" if lan_enabled else "127.0.0.1",
        "mode": "lan_whitelist" if lan_enabled else "local_only",
        "allowed_ips": prefs.allowed_ips if prefs else "",
        "allowed_subnets": prefs.allowed_subnets if prefs else "",
    }


def restart_server_if_running(context=None):
    context = context or bpy.context
    scene = getattr(context, "scene", None)
    if scene is None or not getattr(scene, "blendermcp_server_running", False):
        return
    prefs = get_addon_preferences(context)
    if not prefs or not prefs.auth_token:
        return
    try:
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server
        config = build_network_config(prefs)
        bpy.types.blendermcp_server = blendermcp_server.BlenderMCPServer(
            host=config["host"],
            port=scene.blendermcp_port,
            addon_module_name=ADDON_MODULE_NAME,
        )
        bpy.types.blendermcp_server.start()
    except Exception as exc:
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            try:
                bpy.types.blendermcp_server.stop()
                del bpy.types.blendermcp_server
            except Exception:
                pass
        scene.blendermcp_server_running = False
        print(f"BlenderMCP network reconfiguration failed: {exc}")


def on_network_security_changed(self, context):
    if getattr(self, "_network_update_lock", False):
        return
    self._network_update_lock = True
    try:
        if self.lan_mode_enabled:
            self.local_only_mode = False
        elif not self.local_only_mode:
            self.local_only_mode = True
        restart_server_if_running(context)
    finally:
        self._network_update_lock = False


class BLENDERMCP_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_MODULE_NAME

    auth_token: StringProperty(name="Auth Token", subtype="PASSWORD", default="")
    safe_file_roots: StringProperty(
        name="Safe File Roots",
        description="OS-path-separated list of additional roots allowed for local file reads",
        default=os.path.join(os.path.expanduser("~"), "BlenderMCP", "inputs"),
    )
    local_only_mode: BoolProperty(
        name="Local-Only Mode",
        description="Bind the MCP server to 127.0.0.1 only",
        default=True,
        update=on_network_security_changed,
    )
    lan_mode_enabled: BoolProperty(
        name="Enable LAN Whitelist Mode",
        description="Bind for LAN access, but only allow explicitly whitelisted IPs and subnets",
        default=False,
        update=on_network_security_changed,
    )
    allowed_ips: StringProperty(
        name="Allowed IPs",
        description="Comma-separated explicit client IPs allowed in LAN whitelist mode",
        default="",
        update=on_network_security_changed,
    )
    allowed_subnets: StringProperty(
        name="Allowed Subnets",
        description="Comma-separated CIDR subnets allowed in LAN whitelist mode",
        default="",
        update=on_network_security_changed,
    )
    telemetry_consent: BoolProperty(
        name="Allow Telemetry",
        description="Allow collection of prompts, code snippets, and screenshots to help improve Blender MCP",
        default=False,
    )
    hyper3d_api_key: StringProperty(name="Hyper3D API Key", subtype="PASSWORD", default="")
    sketchfab_api_key: StringProperty(name="Sketchfab API Key", subtype="PASSWORD", default="")
    hunyuan_secret_id: StringProperty(name="Hunyuan SecretId", default="")
    hunyuan_secret_key: StringProperty(name="Hunyuan SecretKey", subtype="PASSWORD", default="")

    def draw(self, _context):
        layout = self.layout
        layout.label(text="Security", icon="LOCKED")
        box = layout.box()
        box.prop(self, "auth_token", text="Auth Token")
        row = box.row(align=True)
        row.operator("blendermcp.generate_auth_token", text="Generate")
        row.prop(self, "local_only_mode")
        box.prop(self, "lan_mode_enabled")
        if self.lan_mode_enabled:
            box.prop(self, "allowed_ips")
            box.prop(self, "allowed_subnets")
        box.prop(self, "safe_file_roots")
        box.label(text="Local-only is the default and safest mode.", icon="INFO")
        box.label(text="LAN mode requires token auth and IP/CIDR allowlists.", icon="INFO")
        box.label(text="Local file reads are restricted to the configured safe roots.", icon="INFO")

        layout.separator()
        layout.label(text="Provider Secrets", icon="KEYINGSET")
        box = layout.box()
        box.prop(self, "hyper3d_api_key")
        box.prop(self, "sketchfab_api_key")
        box.prop(self, "hunyuan_secret_id")
        box.prop(self, "hunyuan_secret_key")

        layout.separator()
        layout.label(text="Telemetry", icon="PREFERENCES")
        box = layout.box()
        box.prop(self, "telemetry_consent")
        box.label(text="Telemetry is disabled by default.", icon="INFO")


class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BlenderMCP"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = get_addon_preferences(context)

        layout.label(text="Server", icon="NETWORK_DRIVE")
        box = layout.box()
        box.prop(scene, "blendermcp_port")
        if prefs and prefs.lan_mode_enabled:
            box.label(text="Mode: LAN whitelist enabled", icon="NETWORK_DRIVE")
            box.label(text="Binding: 0.0.0.0 with IP/CIDR allowlists")
        else:
            box.label(text="Mode: local only", icon="LOCKED")
            box.label(text="Binding: 127.0.0.1 only")
        if prefs and prefs.auth_token:
            box.label(text="Auth token configured", icon="CHECKMARK")
        else:
            box.label(text="Set an auth token in add-on preferences", icon="ERROR")

        row = box.row(align=True)
        if not scene.blendermcp_server_running:
            row.operator("blendermcp.start_server", text="Start Server")
        else:
            row.operator("blendermcp.stop_server", text="Stop Server")
            host = "0.0.0.0" if prefs and prefs.lan_mode_enabled else "127.0.0.1"
            box.label(text=f"Listening on {host}:{scene.blendermcp_port}")

        layout.separator()
        layout.label(text="Providers", icon="WORLD")
        box = layout.box()
        box.prop(scene, "blendermcp_use_polyhaven", text="Use Poly Haven")
        box.prop(scene, "blendermcp_use_hyper3d", text="Use Hyper3D Rodin")
        if scene.blendermcp_use_hyper3d:
            box.prop(scene, "blendermcp_hyper3d_mode", text="Mode")

        box.prop(scene, "blendermcp_use_sketchfab", text="Use Sketchfab")
        box.prop(scene, "blendermcp_use_hunyuan3d", text="Use Tencent Hunyuan 3D")
        if scene.blendermcp_use_hunyuan3d:
            box.prop(scene, "blendermcp_hunyuan3d_mode", text="Mode")
            if scene.blendermcp_hunyuan3d_mode == "LOCAL_API":
                box.prop(scene, "blendermcp_hunyuan3d_api_url", text="API URL")
                box.prop(scene, "blendermcp_hunyuan3d_octree_resolution", text="Octree Resolution")
                box.prop(scene, "blendermcp_hunyuan3d_num_inference_steps", text="Inference Steps")
                box.prop(scene, "blendermcp_hunyuan3d_guidance_scale", text="Guidance Scale")
                box.prop(scene, "blendermcp_hunyuan3d_texture", text="Generate Texture")

        layout.separator()
        layout.operator("screen.userpref_show", text="Open Add-on Preferences", icon="PREFERENCES")


class BLENDERMCP_OT_GenerateAuthToken(bpy.types.Operator):
    bl_idname = "blendermcp.generate_auth_token"
    bl_label = "Generate Auth Token"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        if not prefs:
            self.report({"ERROR"}, "Addon preferences are unavailable")
            return {"CANCELLED"}
        prefs.auth_token = secrets.token_urlsafe(24)
        self.report({"INFO"}, "Auth token generated")
        return {"FINISHED"}


class BLENDERMCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Start Blender MCP Server"

    def execute(self, context):
        scene = context.scene
        prefs = get_addon_preferences(context)
        if not prefs or not prefs.auth_token:
            self.report({"ERROR"}, "Configure an auth token in add-on preferences before starting the server")
            return {"CANCELLED"}
        if prefs.lan_mode_enabled and not (prefs.allowed_ips.strip() or prefs.allowed_subnets.strip()):
            self.report({"ERROR"}, "LAN whitelist mode requires at least one allowed IP or subnet")
            return {"CANCELLED"}

        config = build_network_config(prefs)
        if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
            bpy.types.blendermcp_server = blendermcp_server.BlenderMCPServer(
                host=config["host"],
                port=scene.blendermcp_port,
                addon_module_name=ADDON_MODULE_NAME,
            )
        try:
            bpy.types.blendermcp_server.start()
        except Exception as exc:
            scene.blendermcp_server_running = False
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        scene.blendermcp_server_running = True
        self.report({"INFO"}, f"Server listening on {config['host']}:{scene.blendermcp_port}")
        return {"FINISHED"}


class BLENDERMCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop Blender MCP Server"

    def execute(self, context):
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server
        context.scene.blendermcp_server_running = False
        self.report({"INFO"}, "Server stopped")
        return {"FINISHED"}


CLASSES = (
    BLENDERMCP_AddonPreferences,
    BLENDERMCP_PT_Panel,
    BLENDERMCP_OT_GenerateAuthToken,
    BLENDERMCP_OT_StartServer,
    BLENDERMCP_OT_StopServer,
)


def register():
    bpy.types.Scene.blendermcp_port = IntProperty(name="Port", default=9876, min=1024, max=65535)
    bpy.types.Scene.blendermcp_server_running = BoolProperty(name="Server Running", default=False)
    bpy.types.Scene.blendermcp_use_polyhaven = BoolProperty(name="Use Poly Haven", default=False)
    bpy.types.Scene.blendermcp_use_hyper3d = BoolProperty(name="Use Hyper3D Rodin", default=False)
    bpy.types.Scene.blendermcp_hyper3d_mode = EnumProperty(
        name="Hyper3D Mode",
        items=(
            ("MAIN_SITE", "hyper3d.ai", "Use Hyper3D main site"),
            ("FAL_AI", "fal.ai", "Use fal.ai"),
        ),
        default="MAIN_SITE",
    )
    bpy.types.Scene.blendermcp_use_sketchfab = BoolProperty(name="Use Sketchfab", default=False)
    bpy.types.Scene.blendermcp_use_hunyuan3d = BoolProperty(name="Use Hunyuan 3D", default=False)
    bpy.types.Scene.blendermcp_hunyuan3d_mode = EnumProperty(
        name="Hunyuan Mode",
        items=(
            ("LOCAL_API", "Local API", "Use a local Hunyuan service"),
            ("OFFICIAL_API", "Official API", "Use Tencent official API"),
        ),
        default="LOCAL_API",
    )
    bpy.types.Scene.blendermcp_hunyuan3d_api_url = StringProperty(name="API URL", default="http://127.0.0.1:8081")
    bpy.types.Scene.blendermcp_hunyuan3d_octree_resolution = IntProperty(name="Octree Resolution", default=256, min=128, max=512)
    bpy.types.Scene.blendermcp_hunyuan3d_num_inference_steps = IntProperty(name="Inference Steps", default=20, min=20, max=50)
    bpy.types.Scene.blendermcp_hunyuan3d_guidance_scale = FloatProperty(name="Guidance Scale", default=5.5, min=1.0, max=10.0)
    bpy.types.Scene.blendermcp_hunyuan3d_texture = BoolProperty(name="Generate Texture", default=False)

    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
        bpy.types.blendermcp_server.stop()
        del bpy.types.blendermcp_server

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.blendermcp_port
    del bpy.types.Scene.blendermcp_server_running
    del bpy.types.Scene.blendermcp_use_polyhaven
    del bpy.types.Scene.blendermcp_use_hyper3d
    del bpy.types.Scene.blendermcp_hyper3d_mode
    del bpy.types.Scene.blendermcp_use_sketchfab
    del bpy.types.Scene.blendermcp_use_hunyuan3d
    del bpy.types.Scene.blendermcp_hunyuan3d_mode
    del bpy.types.Scene.blendermcp_hunyuan3d_api_url
    del bpy.types.Scene.blendermcp_hunyuan3d_octree_resolution
    del bpy.types.Scene.blendermcp_hunyuan3d_num_inference_steps
    del bpy.types.Scene.blendermcp_hunyuan3d_guidance_scale
    del bpy.types.Scene.blendermcp_hunyuan3d_texture


if __name__ == "__main__":
    register()
