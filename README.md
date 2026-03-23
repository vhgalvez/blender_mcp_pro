# Blender MCP Pro

Blender MCP Pro is a compact Blender add-on that exposes a secure local MCP-style command server for scene inspection, provider integrations, character blockouts, prop blockouts, and simple environment layouts.

The current codebase is intentionally small. It focuses on a practical secure transport layer, editable Blender geometry, and a narrow set of debuggable workflows. It does not claim advanced AI vision, autonomous orchestration, or full production pipelines yet.

## Repository Layout

The repository keeps documentation and git metadata at the root, and the installable Blender add-on lives inside the `blender_mcp_pro/` package folder:

```text
blender-mcp-pro/
├── .gitignore
├── LICENSE
├── README.md
├── SECURITY.md
└── blender_mcp_pro/
    ├── __init__.py
    ├── addon.py
    ├── server.py
    ├── protocol.py
    ├── dispatcher.py
    ├── integrations.py
    ├── file_ops.py
    └── character_tools.py
```

What each file does:

- `__init__.py`: Blender package entrypoint that exposes `bl_info`, `register`, and `unregister`.
- `addon.py`: Blender UI, add-on preferences, security/network preferences, operators, register/unregister.
- `server.py`: socket lifecycle, local-only or LAN-whitelist binding, client admission checks, auth flow, audit logging, main-thread call bridge.
- `protocol.py`: NDJSON framing, request validation, command schemas, message size limits, structured errors.
- `dispatcher.py`: secure allowlist router plus compact props/environment builders.
- `integrations.py`: outbound provider HTTP logic for Poly Haven, Sketchfab, Rodin, and Hunyuan.
- `file_ops.py`: safe file roots, screenshot path restrictions, temp files, downloads, ZIP extraction, import helpers.
- `character_tools.py`: character references, blockout, symmetry, hair, face, materials, review screenshots, comparison, and proportion fixes.

## Security Model

The current implementation is built around a local-first security model:

- Local-only mode is the default and safest mode.
- Optional LAN whitelist mode can be enabled manually.
- Every client must authenticate with a shared token.
- Incoming messages use structured NDJSON with validation and size limits.
- Local file reads are restricted to configured safe roots.
- Screenshots are restricted to `~/BlenderMCP/screenshots`.
- Client admissions and rejections are audit-logged to `~/BlenderMCP/audit.log`.

### Local-Only Mode

- Server binds to `127.0.0.1`
- Only loopback clients are accepted
- Token auth is still required

### Optional LAN Whitelist Mode

- Disabled by default
- Must be enabled manually in add-on preferences
- Requires at least one allowed IP or CIDR subnet
- Still requires token auth for every client
- No public internet mode exists

Examples:

- Allowed IPs: `192.168.1.10,192.168.1.25`
- Allowed subnets: `192.168.1.0/24,10.0.0.0/24`

For full security details, see [SECURITY.md](SECURITY.md).

## Installation

Requirements:

- Blender 3.x or newer
- A ZIP that contains the add-on package folder

### Package Folder Layout

Blender installs modular add-ons as Python packages. The ZIP must contain a single top-level package folder with a valid Python module name.

Recommended package folder name:

```text
blender_mcp_pro/
```

Expected ZIP contents:

```text
blender_mcp_pro.zip
└── blender_mcp_pro/
    ├── __init__.py
    ├── addon.py
    ├── server.py
    ├── protocol.py
    ├── dispatcher.py
    ├── integrations.py
    ├── file_ops.py
    └── character_tools.py
```

Do not create a ZIP with loose `.py` files at the root. Do not create a ZIP where the add-on files are nested under an extra repository folder unless that inner folder is the actual package folder Blender should import.

### Creating The ZIP

From a working copy, ZIP the `blender_mcp_pro/` folder itself so that the folder is the top-level entry in the archive. Keep `README.md`, `SECURITY.md`, `LICENSE`, and git metadata at the repository root; they are not required inside the Blender install ZIP.

Correct:

```text
blender_mcp_pro.zip
└── blender_mcp_pro/
```

Incorrect:

```text
blender_mcp_pro.zip
├── addon.py
├── server.py
└── ...
```

Incorrect:

```text
blender_mcp_pro.zip
└── blender-mcp-pro-main/
    └── blender_mcp_pro/
```

### Installing In Blender

1. Open Blender.
2. Go to `Edit > Preferences > Add-ons`.
3. Click `Install...`.
4. Select the ZIP file that contains the `blender_mcp_pro` package folder.
5. Enable the add-on.
6. Open the `BlenderMCP` tab in the 3D View sidebar.
7. Open add-on preferences and set an `Auth Token` before starting the server.

### Troubleshooting Import Errors

If Blender reports errors such as `No module named 'server'` or similar:

- Make sure the ZIP contains the package folder, not loose files.
- Make sure the package folder contains `__init__.py`.
- Make sure the package folder name is a valid Python package name such as `blender_mcp_pro`.
- Remove any older broken install of the add-on from Blender before reinstalling.
- Recreate the ZIP after any file moves so Blender is not reading a stale archive.

If Blender reports `attempted relative import with no known parent package`:

- Make sure Blender is installing the ZIP as a package folder, not a single loose Python file.
- Make sure you selected the ZIP that contains `blender_mcp_pro/` at the top level.
- Do not run the individual module files directly; Blender must load the package through `blender_mcp_pro/__init__.py`.

The previous import failure happened because the add-on was being loaded as a package, but the code was importing sibling modules as top-level modules like `import server` and `from dispatcher import ...`. In a packaged Blender add-on, those imports must be package-relative, such as `from . import server` and `from .dispatcher import ...`.

## Secure Usage

### Same PC

Recommended setup:

1. Keep `Local-Only Mode` enabled.
2. Generate an `Auth Token` in add-on preferences.
3. Leave LAN whitelist mode disabled.
4. Start the server from the Blender panel.
5. Connect your local MCP client using `127.0.0.1:<port>` and the token.

### Optional LAN Use For Another Laptop Or PC

Only use this on a trusted local network.

1. Generate or rotate the `Auth Token`.
2. Enable `Enable LAN Whitelist Mode`.
3. Add the exact remote machine IP to `Allowed IPs`, or a narrow trusted subnet to `Allowed Subnets`.
4. Start or restart the server.
5. Connect from the other machine using the Blender host LAN IP and the same token.
6. Disable LAN whitelist mode again when the session is over.

Do not expose the server through router port forwarding, reverse proxies, or public tunnels.

## Current Command Model

The command layer currently supports three practical modes:

- `character`
- `props`
- `environment`

Character commands are implemented in `character_tools.py`. Props and environment commands are implemented compactly in `dispatcher.py`.

## Character Workflow

Current character workflow:

1. `load_character_references`
2. `create_character_blockout`
3. `apply_character_symmetry`
4. `build_character_hair`
5. `build_character_face`
6. `apply_character_materials`
7. `capture_character_review`
8. `compare_character_with_references`
9. `apply_character_proportion_fixes`

What it supports today:

- front / side / optional back reference images
- stylized cartoon blockout
- mirror workflow
- simple punk/spiky hair
- simple cartoon face parts
- simple base materials
- front/side review screenshots
- heuristic silhouette comparison
- non-destructive scale-based proportion fixes

Character generation is still heuristic and geometry-based. There is no advanced image understanding or ML-based character reconstruction yet.

## Props Workflow

Current props mode commands:

- `create_prop_blockout`
- `apply_prop_symmetry`
- `apply_prop_materials`

Supported prop blockout types:

- `chair`
- `table`
- `crate`
- `weapon`

What props mode does today:

- creates named editable prop geometry
- groups prop objects cleanly
- supports a mirror workflow
- applies simple stylized base materials

## Environment Workflow

Current environment mode commands:

- `create_environment_layout`
- `apply_environment_materials`

Supported layout types:

- `room`
- `corridor`
- `shop`
- `kiosk`

What environment mode does today:

- creates editable layout geometry
- groups environment objects cleanly
- applies simple base materials for floors, walls, counters, and accents

## Provider Integrations

The current add-on includes practical provider integration support for:

- Poly Haven
- Sketchfab
- Hyper3D / Rodin
- Hunyuan

These integrations are still guarded by the same secure transport and preference model, and they are intentionally separate from the geometry-first character/props/environment workflows.

## What Is Not Implemented Yet

The README now intentionally avoids claiming the following as finished:

- advanced image understanding
- ML or external vision models for character analysis
- autonomous feedback loops
- advanced procedural generation
- advanced asset orchestration
- full scene pipeline automation
- public internet access mode
- open access / unauthenticated mode
- per-command authorization tiers
- rate limiting
- protocol version negotiation
- advanced character features beyond the current stylized editable foundation

## Current Status

The project currently provides:

- a real 7-file compact architecture
- a secure local-first command server
- optional LAN whitelist access
- character workflow phase 1 to 3
- multipurpose phase 1 for props and environment

It does not yet provide a full autonomous 3D generation platform.


🔐 Authentication Token (Required)

The MCP server requires a shared authentication token before it can accept and execute any client commands.

This token is not generated externally and does not come from any provider.
It is a manually defined shared secret between Blender and your MCP client.

How To Create A Token

You can use any string, but it is recommended to use a unique and non-trivial value.

Option 1 — Simple (for testing)
123456
Option 2 — Custom secure string (recommended)
mcp_secure_token_2026_victor
Option 3 — Random token (recommended for real use)

Generate a UUID in PowerShell:

[guid]::NewGuid()

Example output:

b7f3c2a1-9c4d-4f2e-a8e1-6d9c2b7a1234
Where To Set The Token
Open Blender
Go to the MCP panel in the 3D View sidebar (N key → Blender MCP tab)
Click:
Open Add-on Preferences
Find the field:
Auth Token
Paste your token there
Why The Token Is Required

The MCP server uses the token to authenticate every client connection.

Without a valid token:

the server will reject the connection
no commands will be executed
the client will be logged as rejected in the audit log
Example Client Authentication

A client must authenticate before sending any command:

{
  "type": "auth",
  "token": "mcp_secure_token_2026_victor"
}

The token must match exactly the one configured in Blender.

Security Notes
Never expose your token in public repositories
Rotate the token if you enable LAN whitelist mode
Use a strong random token when connecting multiple machines
The token is required even in local-only mode
💡 EXTRA (recomendación PRO)

También puedes añadir esta línea en tu README arriba:

> ⚠️ The server will not start until a valid Auth Token is set in the add-on preferences.