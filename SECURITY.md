# Security Notes

## Threat Model

This add-on is designed for a trusted local Blender environment with a local MCP client on the same machine.

The primary threats considered in the current implementation are:

- unauthenticated local client access
- malformed or oversized protocol messages
- arbitrary file writes through screenshot export
- arbitrary local file reads through provider image inputs
- arbitrary local file reads through character reference inputs
- unsafe ZIP extraction from remote provider downloads
- accidental credential persistence inside `.blend` scene data

The current implementation does not attempt to defend against a fully compromised local machine.

## Local-Only Guarantees

- The server binds to `127.0.0.1` only.
- `Local-Only Mode` is the default and safest mode.
- In local-only mode, only loopback clients such as `127.0.0.1` and `::1` are accepted.
- Disabling LAN whitelist mode returns the server to local-only behavior immediately.

## LAN Whitelist Behavior

- LAN access is optional and disabled by default.
- When `Enable LAN Whitelist Mode` is enabled, the server binds for LAN access and still requires token authentication.
- Only clients whose IP addresses match the configured allowlists may connect.
- `Allowed IPs` accepts explicit comma-separated addresses such as `192.168.1.10,192.168.1.20`.
- `Allowed Subnets` accepts comma-separated CIDR ranges such as `192.168.1.0/24,10.0.0.0/24`.
- There is no open-access mode and no public-internet mode.
- If LAN whitelist mode has no allowed IPs or subnets configured, the server will not start in that mode.

## Token Requirements

- Every client must authenticate first with a shared auth token.
- No command message is accepted before authentication succeeds.
- Auth failures are audit-logged without logging the token itself.
- The token is stored in add-on preferences, not scene properties.
- The recommended VS Code setup loads client-side connection settings from `client/.env` via `.vscode/mcp.json` instead of hardcoding the token in workspace config.

## File Access Restrictions

- Screenshots are restricted to `~/BlenderMCP/screenshots`.
- Character review screenshots use the same restricted screenshot directory.
- Local file reads are restricted to configured safe roots.
- The default safe root is `~/BlenderMCP/inputs`.
- Additional safe roots can be configured in add-on preferences using the OS path separator.
- Local file reads reject symlinks, unsupported extensions, and oversized files.
- Character reference images use the same safe-root restrictions as provider image inputs.
- ZIP extraction is centralized and hardened against traversal and symlink attacks.

## Safe Usage Guidance

- Prefer local-only mode unless you explicitly need another trusted machine on your LAN to connect.
- If LAN whitelist mode is needed, use the narrowest possible explicit IP or CIDR entries.
- Keep the auth token unique and rotate it after temporary LAN access sessions.
- Disable LAN whitelist mode as soon as the remote session is finished.
- Do not expose this server through router port forwarding, VPN auto-bridging, or public reverse proxies.

## Protocol Restrictions

- The transport is NDJSON only.
- The production Copilot path is stdio MCP in `client/mcp_stdio_server.py`, which bridges into the authenticated TCP backend.
- Every message must include a non-empty string request id.
- Malformed JSON, invalid UTF-8, oversized messages, and unsupported fields are rejected with structured error codes.
- Unknown commands and invalid params are rejected.

## Command Risk Levels

Low risk:

- `get_scene_info`
- `get_object_info`
- `get_telemetry_consent`
- `get_polyhaven_status`
- `get_hyper3d_status`
- `get_sketchfab_status`
- `get_hunyuan3d_status`
- `get_polyhaven_categories`
- `search_polyhaven_assets`
- `search_sketchfab_models`
- `get_sketchfab_model_preview`
- `poll_rodin_job_status`
- `poll_hunyuan_job_status`

Medium risk:

- `get_viewport_screenshot`
  - writes a file, but only inside the managed screenshot directory
- `create_rodin_job`
  - triggers outbound provider requests and may send user-supplied prompts or URLs
- `create_hunyuan_job`
  - can read a local image file, but only from configured safe roots
- `load_character_references`
  - can read local image files, but only from configured safe roots
- `create_character_blockout`
  - creates named scene geometry for a character base
- `build_character_hair`
  - creates editable stylized hair geometry
- `build_character_face`
  - creates editable stylized facial geometry and optional piercings
- `apply_character_materials`
  - creates and assigns predictable base materials to character geometry
- `capture_character_review`
  - captures review screenshots only into the managed screenshot directory
- `compare_character_with_references`
  - reads already loaded in-Blender reference images and produces heuristic correction data
- `apply_character_proportion_fixes`
  - performs non-destructive scale-based adjustments on named character objects
- `apply_character_symmetry`
  - configures mirror modifiers on mesh objects
- `create_prop_blockout`
  - creates named editable prop geometry in a dedicated collection
- `apply_prop_symmetry`
  - configures mirror modifiers on prop meshes
- `apply_prop_materials`
  - creates and assigns simple prop materials
- `create_environment_layout`
  - creates named editable environment layout geometry in a dedicated collection
- `apply_environment_materials`
  - creates and assigns simple environment materials

High risk:

- `download_polyhaven_asset`
- `set_texture`
- `import_generated_asset`
- `download_sketchfab_model`
- `import_generated_asset_hunyuan`
- `clear_character_references`

These commands import assets, mutate the scene, or process remote archives.

## Not Implemented Yet

- per-command authorization or role separation
- request rate limiting
- protocol version negotiation
- command cancellation and progress channels
- advanced character-generation features such as image understanding, richer procedural modeling, and autonomous refinement
