# Blender MCP Pro

Blender MCP Pro is split into two real layers:

1. `blender_mcp_pro/`
   The Blender add-on. It owns the authenticated TCP backend and all Blender-side primitives.
2. `client/`
   The external TCP client, MCP stdio bridge, and generative orchestration layer used by VS Code Copilot.

The intended production path is:

```text
VS Code Copilot Agent
-> .vscode/mcp.json
-> client/mcp_stdio_server.py
-> client/blender_client.py
-> blender_mcp_pro/ backend
-> Blender
```

## Repository Layout

```text
.
├── .vscode/
│   └── mcp.json
├── blender_mcp_pro/
│   ├── __init__.py
│   ├── addon.py
│   ├── character_tools.py
│   ├── dispatcher.py
│   ├── file_ops.py
│   ├── integrations.py
│   ├── protocol.py
│   ├── server.py
│   └── tool_registry.py
├── client/
│   ├── .env
│   ├── agent_cli.py
│   ├── blender_client.py
│   ├── mcp_adapter.py
│   ├── mcp_stdio_server.py
│   ├── smoke_test.py
│   └── tools_registry.py
├── README.md
└── SECURITY.md
```

## What Gets Installed Into Blender

Install only `blender_mcp_pro/` as the Blender add-on.

Do not install `client/` into Blender. `client/` stays outside Blender and is launched by VS Code or a local terminal.

## Backend vs Bridge

`blender_mcp_pro/` contains the real backend:

- token-authenticated TCP server
- local-only by default
- optional LAN allowlist mode
- safe local file restrictions
- Blender-side primitives

`client/` contains the external bridge:

- `blender_client.py`: minimal TCP client
- `mcp_stdio_server.py`: MCP stdio server for VS Code Copilot
- `tools_registry.py`: authoritative exposed MCP tool registry
- `mcp_adapter.py`: natural-language routing and generative orchestration
- `agent_cli.py`: local debugging interface
- `smoke_test.py`: backend verification only

## Tool Model

The public MCP surface is intentionally smaller than the raw backend command surface.

### Primitive Tools

Examples:

- `scene_info`
- `object_info`
- `viewport_screenshot`
- `integration_status`
- `search_assets`
- `import_asset`
- `create_primitive`
- `move_object`
- `rotate_object`
- `scale_object`
- `apply_material`
- `create_light`
- `set_camera`
- `create_prop_blockout`
- `apply_prop_materials`
- `create_environment_layout`
- `apply_environment_materials`
- character reference/blockout/review primitives

These are the reliable, composable building blocks.

### Generative Tools

Examples:

- `generate_scene_plan`
- `apply_scene_plan`
- `build_scene_from_description`
- `build_character_from_description`
- `create_character_from_references`
- `review_and_fix_character`

These do not invent hidden backend commands. They only orchestrate real primitives.

## Quick Start

1. Package `blender_mcp_pro/` as a Blender add-on ZIP and install it in Blender.
2. Enable the add-on.
3. Generate or set an auth token in add-on preferences.
4. Start the Blender MCP server from the add-on panel.
5. Fill `client/.env` locally:

```env
BLENDER_HOST=127.0.0.1
BLENDER_PORT=9876
BLENDER_TOKEN=your_real_token_here
BLENDER_TIMEOUT_SECONDS=10.0
```

6. From the repository root, verify the backend:

```powershell
python client/smoke_test.py
```

7. For local debugging:

```powershell
python client/agent_cli.py
```

8. For MCP stdio:

```powershell
python client/mcp_stdio_server.py
```

## VS Code Copilot Integration

`.vscode/mcp.json` should point to the stdio bridge, not directly to Blender:

```json
{
  "servers": {
    "blender-mcp-pro": {
      "type": "stdio",
      "command": "python",
      "args": ["client/mcp_stdio_server.py"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}/client/.env",
      "env": {
        "BLENDER_HOST": "127.0.0.1",
        "BLENDER_PORT": "9876"
      }
    }
  }
}
```

This is the correct Copilot path because the bridge exposes the curated primitive and generative tool set.

## Testing

### Backend Only

```powershell
python client/smoke_test.py
python client/smoke_test.py --with-character
```

This verifies:

- TCP connectivity
- auth token handling
- real backend command execution

### MCP Bridge

Run:

```powershell
python client/mcp_stdio_server.py
```

Then send MCP JSON-RPC requests from a client or let VS Code launch it.

### Copilot Agent

1. Start Blender and the add-on server.
2. Make sure `client/.env` has the right token.
3. Open the repo in VS Code.
4. Reload the MCP server from `.vscode/mcp.json`.
5. Use Copilot Agent against `blender-mcp-pro`.

## Natural-Language Examples

Supported patterns are routed to primitives or generative tools, for example:

- `crea una habitación low poly con cama y escritorio`
- `hazme una tienda pequeña con mostrador`
- `create a stylized room with warm sunset lighting`
- `create a punk cartoon character`

If a capability is not actually implemented, the bridge returns a structured limitation payload with suggestions instead of pretending the feature exists.

## Troubleshooting

### `smoke_test.py` passes but Copilot still behaves rigidly

That usually means the backend is fine and the issue is one of:

- VS Code is not launching `.vscode/mcp.json`
- `client/.env` has the wrong token
- Copilot is talking to stale tool metadata
- the request should be using a generative tool like `build_scene_from_description` instead of a low-level primitive

Check:

1. `python client/mcp_stdio_server.py` starts cleanly.
2. `.vscode/mcp.json` points to `client/mcp_stdio_server.py`.
3. `BLENDER_TOKEN` in `client/.env` matches the Blender add-on token.
4. VS Code MCP output shows `tools/list` succeeding.

### The bridge starts but tool calls fail

Check:

- Blender add-on server is running
- host/port/token match
- the requested capability is real

The bridge only exposes working tools or returns a structured limitation error.

## Current Limits

Not implemented:

- arbitrary Python execution
- fully autonomous 3D generation
- full image-to-3D reconstruction from local prompts alone
- dedicated street layout primitives

Implemented:

- safe local TCP backend
- curated MCP stdio bridge for Copilot
- primitive scene/prop/environment/character tools
- small generative planning layer on top of real primitives
