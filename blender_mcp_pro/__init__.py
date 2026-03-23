bl_info = {
    "name": "Blender MCP",
    "author": "BlenderMCP",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Blender MCP",
    "description": "Connect Blender to local MCP clients with authenticated commands.",
    "category": "Interface",
}

from .addon import register, unregister
