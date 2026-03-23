bl_info = {
    "name": "Blender MCP",
    "author": "BlenderMCP",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Blender MCP",
    "description": "Connect Blender to local MCP clients with authenticated commands.",
    "category": "Interface",
}

try:
    from .addon import register, unregister
except ImportError:
    # Allow non-Blender Python processes to import shared metadata modules.
    def register():
        raise RuntimeError("Blender register() is only available inside Blender")

    def unregister():
        raise RuntimeError("Blender unregister() is only available inside Blender")
