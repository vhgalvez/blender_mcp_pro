# Security Notes

## Security Model

Blender MCP Pro is designed for a local-first Blender workflow.

The backend security boundary is the Blender add-on in `blender_mcp_pro/`. The external `client/` bridge is not trusted to bypass backend restrictions; it must authenticate like any other client.

Core properties:

- token authentication is mandatory
- local-only networking is the default
- optional LAN mode is allowlist-based
- local file reads are restricted to configured safe roots
- screenshot writes are restricted to the managed screenshot directory
- remote archive extraction is hardened against traversal and symlink attacks

## Network Exposure

### Default Mode

- bind address: `127.0.0.1`
- accepted clients: loopback only
- auth token: still required

### Optional LAN Whitelist Mode

- disabled by default
- still requires token auth
- requires at least one allowed IP or CIDR subnet
- no public-internet mode exists

Do not expose this service through router forwarding, reverse proxies, or public tunnels.

## Token Handling

- The token is stored in Blender add-on preferences, not scene properties.
- The recommended client-side storage is `client/.env`.
- Do not commit real tokens to source control.
- Rotate the token after temporary LAN sessions.

## File Access Restrictions

Local file reads are limited to configured safe roots.

Default safe root:

- `~/BlenderMCP/inputs`

Restrictions:

- files only, not directories
- no symlinks
- extension allowlists
- size limits

Screenshot output is limited to:

- `~/BlenderMCP/screenshots`

## Bridge Behavior

The main MCP entrypoint for VS Code is:

- `client/mcp_stdio_server.py`

That bridge does not expand backend privilege. It translates MCP stdio requests into authenticated TCP calls against Blender and applies a curated exposed tool registry.

The generative layer in `client/mcp_adapter.py` only orchestrates real primitives. It does not grant arbitrary code execution and does not invent hidden commands.

## Risk Levels

### Lower Risk

- `scene_info`
- `object_info`
- `telemetry_consent`
- `integration_status`

### Medium Risk

- `viewport_screenshot`
- `create_primitive`
- `move_object`
- `rotate_object`
- `scale_object`
- `apply_material`
- `create_light`
- `set_camera`
- prop/environment/character blockout and review primitives
- `search_assets`

### Higher Risk

- `import_asset`
- backend provider download/import commands
- texture import/application flows

These mutate the Blender scene and may download or import external content.

## What Is Intentionally Not Allowed

- unauthenticated commands
- unrestricted filesystem access
- arbitrary output paths for screenshots
- unrestricted ZIP extraction
- open LAN or public network access
- arbitrary Python execution through Copilot

## Operational Guidance

Prefer this order when diagnosing problems:

1. Verify backend connectivity with `python client/smoke_test.py`
2. Verify the stdio bridge with `python client/mcp_stdio_server.py`
3. Verify VS Code MCP launch from `.vscode/mcp.json`

If backend tests pass but Copilot fails, treat that as a bridge or editor integration issue, not a reason to weaken auth or file restrictions.
