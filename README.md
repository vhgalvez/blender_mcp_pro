> ⚠️ **Nota:** El servidor no se iniciará hasta que se configure un **Auth Token** válido en las preferencias del complemento.

# Blender MCP Pro

Blender MCP Pro es un complemento compacto para Blender que expone un servidor de comandos local seguro (estilo MCP) para inspección de escenas, integraciones con proveedores, bloqueos de personajes y props, y layouts de entornos simples.

El código es intencionadamente pequeño y enfocado en un transporte seguro, edición de geometría y flujos de trabajo depurables. No implementa aún visión avanzada, orquestación autónoma ni pipelines de producción completos.

---

## Tabla de Contenidos

- [Blender MCP Pro](#blender-mcp-pro)
  - [Tabla de Contenidos](#tabla-de-contenidos)
  - [Estructura del Repositorio](#estructura-del-repositorio)
  - [Modelo de Seguridad](#modelo-de-seguridad)
    - [Modo Local](#modo-local)
    - [Modo LAN Whitelist (opcional)](#modo-lan-whitelist-opcional)
  - [Quick Start](#quick-start)
  - [Architecture](#architecture)
  - [Image-Guided Character Workflow](#image-guided-character-workflow)
  - [Multipurpose Scope](#multipurpose-scope)
  - [Supported MCP Tools](#supported-mcp-tools)
  - [Instalación](#instalación)
  - [Uso Seguro](#uso-seguro)
    - [Mismo PC](#mismo-pc)
    - [LAN (opcional)](#lan-opcional)
  - [Puente MCP STDIO](#puente-mcp-stdio)
  - [Smoke Test](#smoke-test)
  - [End-to-End Test](#end-to-end-test)
  - [Modelo de Comandos](#modelo-de-comandos)
  - [Workflows](#workflows)
    - [Personajes](#personajes)
    - [Props](#props)
    - [Entornos](#entornos)
  - [Integraciones con Proveedores](#integraciones-con-proveedores)
  - [Limitaciones Actuales](#limitaciones-actuales)
  - [Estado Actual](#estado-actual)
  - [Token de Autenticación](#token-de-autenticación)

---

## Estructura del Repositorio

```
blender-mcp-pro/
├── .gitignore
├── LICENSE
├── README.md
├── SECURITY.md
├── client/
│   ├── agent_cli.py
│   ├── blender_client.py
│   ├── mcp_adapter.py
│   ├── smoke_test.py
│   └── tools_registry.py
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

**Descripción de archivos principales:**

- `__init__.py`: Entrada del paquete, expone `bl_info`, `register`, `unregister`.
- `addon.py`: UI, preferencias, operadores, registro.
- `server.py`: Ciclo de vida del socket, autenticación, logging.
- `protocol.py`: Validación, framing NDJSON, límites de tamaño.
- `dispatcher.py`: Router seguro, builders de props/entorno.
- `integrations.py`: Lógica HTTP para proveedores externos.
- `file_ops.py`: Seguridad de archivos, descargas, importación.
- `character_tools.py`: Herramientas de personajes y materiales.
- `client/agent_cli.py`: CLI interactiva para prompts libres, comandos raw y exploración local del toolkit.
- `client/blender_client.py`: Cliente TCP pequeño para autenticarse y enviar comandos al backend de Blender.
- `client/mcp_adapter.py`: Adaptador local para routing de prompts, workflows y despacho de herramientas al backend TCP.
- `client/smoke_test.py`: Smoke test local para validar auth y comandos básicos contra el backend TCP.
- `client/tools_registry.py`: Registro de herramientas MCP locales con descripciones y esquemas JSON.

---

## Modelo de Seguridad

- **Modo local** (por defecto): solo acepta conexiones de `127.0.0.1`.
- **Modo LAN whitelist** (opcional): requiere habilitación manual y lista de IPs/subredes permitidas.
- **Token de autenticación** obligatorio para todos los clientes.
- Validación estricta de mensajes y límites de tamaño.
- Restricción de rutas de archivos y capturas.
- Logging de admisiones y rechazos en `~/BlenderMCP/audit.log`.

### Modo Local

- El servidor escucha en `127.0.0.1`.
- Solo acepta clientes locales.
- El token sigue siendo obligatorio.

### Modo LAN Whitelist (opcional)

- Deshabilitado por defecto.
- Debe habilitarse manualmente en las preferencias del complemento.

- Requiere al menos una IP o subred CIDR permitida.
- El token sigue siendo obligatorio para cada cliente.
- No existe modo de acceso público a Internet.

Ejemplos:

- IPs permitidas: `192.168.1.10,192.168.1.25`
- Subredes permitidas: `192.168.1.0/24,10.0.0.0/24`

Para detalles completos de seguridad, ver [SECURITY.md](SECURITY.md).


---

## Quick Start

1. Instala el ZIP del complemento `blender_mcp_pro` en Blender.
2. Activa el add-on `Blender MCP`.
3. Configura un `Auth Token` en las preferencias del complemento.
4. Inicia el servidor desde el panel del add-on en Blender.
5. En una terminal PowerShell dentro de este repositorio, define:

```powershell
$env:BLENDER_HOST = "127.0.0.1"
$env:BLENDER_PORT = "9876"
$env:BLENDER_TOKEN = "tu_token"
```

6. Ejecuta el bridge MCP:

```powershell
python client/mcp_adapter.py
```

7. Haz el primer smoke test con `get_scene_info`.
8. Haz el primer test con cambio real de escena con `create_prop_blockout`.

Smoke test mínimo:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"quick-start","version":"0.0.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_scene_info","arguments":{}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"create_prop_blockout","arguments":{"prop_type":"table","collection_name":"MCP_QuickStart_Props"}}}
```

---

## Architecture

El flujo actual queda así:

```text
Copilot / Codex MCP Client
            |
            v
client/mcp_adapter.py
(MCP STDIO bridge)
            |
            v
client/blender_client.py
(TCP auth client)
            |
            v
blender_mcp_pro add-on
(Blender backend + TCP server + command execution)
```

Responsabilidades:

- `blender_mcp_pro` dentro de Blender: UI, preferencias, token, validación de red y ejecución real de comandos.
- `client/blender_client.py`: autenticación y llamadas al backend TCP existente.
- `client/mcp_adapter.py`: servidor MCP STDIO compatible con clientes como Copilot/Codex.
- cliente MCP externo: inicia el bridge y consume tools MCP estándar.

---

## Supported MCP Tools

El toolkit local expone herramientas multipropósito agrupadas por dominio.

### Scene / Info

- `get_scene_info`
- `get_object_info`
- `list_collections`:
  placeholder preparado para futuro. El backend actual todavía no expone colecciones.

### Character

- `create_character_from_references`
- `create_character_blockout`
- `capture_character_review`
- `compare_character_with_references`
- `apply_character_proportion_fixes`
- `review_and_fix_character`

### Props

- `create_prop_blockout`
- `apply_prop_materials`

### Environment / Layout

- `create_environment_layout`
- `apply_environment_materials`
- `create_shop_scene`
- `create_room_blockout`
- `create_street_blockout`

### Assets / Integrations

- `search_polyhaven_assets`
- `download_polyhaven_asset`
- `set_texture`

Implementado hoy:

- backend local dentro de Blender con token auth
- cliente TCP local reutilizable
- adaptador local para routing de prompts y workflows
- creación de personajes estilizados guiada por referencias
- blockouts de props e interiores
- revisión y ciclos iterativos de ajuste

No implementado hoy:

- reconstrucción automática completa image-to-3D
- visión avanzada o ML de reconstrucción
- dependencias cloud obligatorias para el flujo local

---

## Character Workflow

El flujo práctico para personaje estilizado guiado por referencias es:

1. `create_character_from_references`
2. `capture_character_review`
3. `compare_character_with_references`
4. `apply_character_proportion_fixes`

También puedes ejecutar pasos individuales como:

- `create_character_blockout`
- `capture_character_review`
- `review_and_fix_character`

Soporta:

- referencias front / side / back o profile
- blockout cartoon / stylized
- pelo y cara estilizados
- materiales base
- revisión por screenshots
- ajustes iterativos de proporciones

No afirma reconstrucción automática de imagen a malla final.

---

## Environment Workflow

El flujo práctico para layout y entorno es:

1. `create_environment_layout`
2. `apply_environment_materials`

Atajos incluidos:

- `create_shop_scene`
- `create_room_blockout`
- `create_street_blockout`

Esto cubre casos útiles como:

- room / bedroom blockouts
- shop / interior layouts
- street-like layouts usando el backend actual de corridor como aproximación local

---

## Multipurpose Usage

El proyecto sigue siendo multipropósito y no está limitado solo a personajes:

- `character`: personajes cartoon / stylized desde reference sheets
- `props`: props básicos para blockout rápido
- `environment`: room / shop / interior / street-like layouts
- `review`: captura, comparación y correcciones
- `assets`: búsqueda y descarga de algunos assets ya soportados por el backend

Esto mantiene útil el toolkit para prototipado de escenas completas en Blender, no solo para un único caso de uso.

---

## Client Directory Layout

El directorio `client/` forma parte de este repositorio `blender_mcp_pro` y debe vivir aquí, no dentro de `.vscode` ni en carpetas sueltas de proyectos no relacionados.

```text
client/
├── agent_cli.py
├── blender_client.py
├── mcp_adapter.py
├── smoke_test.py
└── tools_registry.py
```

---

## Instalación

**Requisitos:**
- Blender 3.x o superior
- ZIP con la carpeta del paquete `blender_mcp_pro/`

**Estructura esperada del ZIP:**
```
blender_mcp_pro.zip
└── blender_mcp_pro/
    ├── __init__.py
    ├── addon.py
    └── ...
```

**Pasos:**
1. Abre Blender.
2. Ve a `Edit > Preferences > Add-ons`.
3. Haz clic en `Install...` y selecciona el ZIP.
4. Activa el complemento.
5. Configura el **Auth Token** en las preferencias antes de iniciar el servidor.

**Solución de errores comunes:**
- El ZIP debe contener la carpeta del paquete, no archivos sueltos.
- La carpeta debe tener `__init__.py` y un nombre válido.
- Elimina instalaciones previas rotas antes de reinstalar.

---


## Uso Seguro

### Mismo PC
1. Mantén el modo local habilitado.
2. Genera y configura un **Auth Token**.
3. Inicia el servidor desde el panel de Blender.
4. Conecta el cliente MCP local usando `127.0.0.1:<puerto>` y el token.

### LAN (opcional)
1. Genera/rota el **Auth Token**.
2. Habilita el modo LAN whitelist.
3. Añade IPs/subredes permitidas.
4. Inicia/reinicia el servidor.
5. Conecta desde otra máquina usando la IP LAN y el token.
6. Deshabilita el modo LAN al terminar.

> **Nunca expongas el servidor a Internet ni uses port forwarding.**

---

## Puente MCP STDIO

El complemento `blender_mcp_pro` sigue siendo el backend dentro de Blender. Su responsabilidad es:

- exponer el servidor TCP local autenticado
- validar red/token
- ejecutar comandos de escena en el hilo principal de Blender

Ese backend **no es MCP nativo** para Copilot/Codex porque habla un protocolo NDJSON propio sobre socket TCP (`auth` + `command`) en lugar de MCP estándar por STDIO y JSON-RPC.

Para resolverlo, el repositorio ahora incluye `client/mcp_adapter.py`, un puente MCP compacto que:

- corre como servidor MCP por STDIO
- lee `BLENDER_HOST`, `BLENDER_PORT` y `BLENDER_TOKEN`
- se conecta al backend TCP ya existente del complemento
- autentica primero
- traduce `tools/call` de MCP a los comandos actuales de Blender

Herramientas MCP expuestas inicialmente:

- `get_scene_info`
- `get_object_info`
- `load_character_references`
- `clear_character_references`
- `create_character_blockout`
- `apply_character_symmetry`
- `build_character_hair`
- `build_character_face`
- `apply_character_materials`
- `capture_character_review`
- `compare_character_with_references`
- `apply_character_proportion_fixes`
- `create_character_from_references`
- `create_prop_blockout`
- `apply_prop_materials`
- `create_environment_layout`
- `apply_environment_materials`
- `get_polyhaven_status`
- `search_polyhaven_assets`
- `download_polyhaven_asset`
- `set_texture`
- `review_and_fix_character`
- `create_shop_scene`

### Uso

1. Instala y habilita el complemento en Blender.
2. Configura el **Auth Token** en preferencias.
3. Inicia el servidor desde el panel del complemento.
4. Configura tu cliente MCP para lanzar:

```powershell
python client/mcp_adapter.py
```

con estas variables de entorno:

```powershell
$env:BLENDER_HOST = "127.0.0.1"
$env:BLENDER_PORT = "9876"
$env:BLENDER_TOKEN = "tu_token"
```

El detalle exacto de configuración depende del cliente MCP, pero la idea es siempre la misma: Copilot/Codex debe arrancar este proceso STDIO, y este proceso reenviará cada tool call al servidor TCP autenticado del add-on.

---

## Smoke Test

El repositorio incluye `client/smoke_test.py` para validar rápidamente el backend TCP local sin depender de un cliente MCP externo.

Variables usadas:

```powershell
$env:BLENDER_HOST = "127.0.0.1"
$env:BLENDER_PORT = "9876"
$env:BLENDER_TOKEN = "tu_token"
```

Ejecutar smoke test básico:

```powershell
python client/smoke_test.py
```

Esto hace:

- auth contra el backend TCP de Blender
- `get_scene_info`
- `create_prop_blockout`

Para incluir también un test de personaje:

```powershell
python client/smoke_test.py --with-character
```

El script imprime `PASS` o `FAIL` por paso para que el primer diagnóstico local sea rápido.

---

## How To Run From The Repository Root

Sitúate en la raíz del repositorio `blender_mcp_pro` y ejecuta los clientes desde ahí.

Ejemplos:

```powershell
python client/smoke_test.py
python client/smoke_test.py --with-character
python client/agent_cli.py
```

CLI interactiva:

- `help`
- `tools`
- `quit`
- `raw get_scene_info {}`
- `create punk character from references`
- `create shop scene`
- `create bedroom blockout`
- `review the character`

---

## End-to-End Test

Pasos exactos para validar el flujo completo `cliente MCP -> bridge STDIO -> backend TCP de Blender -> cambio en escena`:

1. Inicia Blender.
2. Activa el complemento `Blender MCP`.
3. Abre el panel del complemento y pulsa `Start Server`.
4. En una terminal PowerShell, sitúate en este repositorio.
5. Define las variables de entorno que usa el bridge:

```powershell
$env:BLENDER_HOST = "127.0.0.1"
$env:BLENDER_PORT = "9876"
$env:BLENDER_TOKEN = "tu_token"
```

6. Lanza el adaptador MCP por STDIO:

```powershell
python client/mcp_adapter.py
```

7. Desde tu cliente MCP, envía primero `initialize`, luego `notifications/initialized`, y después un primer smoke test con `tools/call` sobre `get_scene_info`.

Ejemplo mínimo por STDIO:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"manual-test","version":"0.0.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_scene_info","arguments":{}}}
```

8. Para verificar un cambio real en la escena, usa después:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"create_prop_blockout","arguments":{"prop_type":"table","collection_name":"MCP_Test_Props"}}}
```

Si todo está bien:

- `get_scene_info` devolverá el resumen de la escena
- `create_prop_blockout` devolverá `success: true`
- en Blender aparecerá la colección y los objetos creados

Para depuración, el bridge escribe logs en `stderr`. Puedes subir el detalle con:

```powershell
$env:BLENDER_MCP_BRIDGE_LOG = "DEBUG"
```

---


## Modelo de Comandos

- `character`
- `props`
- `environment`

---


## Workflows

### Personajes

Comandos:
1. `load_character_references`
2. `create_character_blockout`
3. `apply_character_symmetry`
4. `build_character_hair`
5. `build_character_face`
6. `apply_character_materials`
7. `capture_character_review`
8. `compare_character_with_references`
9. `apply_character_proportion_fixes`

Soporta referencias, bloqueos cartoon, simetría, materiales base, capturas y comparaciones heurísticas.

### Props

Comandos:
- `create_prop_blockout`
- `apply_prop_symmetry`
- `apply_prop_materials`

Tipos soportados: `chair`, `table`, `crate`, `weapon`.

### Entornos

Comandos:
- `create_environment_layout`
- `apply_environment_materials`

Tipos: `room`, `corridor`, `shop`, `kiosk`.

---


## Integraciones con Proveedores

- Poly Haven
- Sketchfab
- Hyper3D / Rodin
- Hunyuan

---


## Limitaciones Actuales

No implementa aún:
- Visión avanzada o ML
- Orquestación autónoma
- Generación procedural avanzada
- Acceso público o sin autenticación
- Rate limiting, negociación de versión, etc.

---

## Estado Actual

- Arquitectura compacta y segura
- Servidor local y whitelist LAN
- Puente MCP STDIO para compatibilidad con clientes MCP locales
- Workflows básicos de personajes, props y entornos

No es aún una plataforma autónoma de generación 3D.

---

## Token de Autenticación

El servidor requiere un **Auth Token** compartido para aceptar comandos.

**Cómo crear un token:**
- Simple: `123456` (solo pruebas)
- Personalizado: `mcp_secure_token_2026_victor`
- Aleatorio (recomendado):  
    En PowerShell:  
    ```
    [guid]::NewGuid()
    ```

**Dónde configurarlo:**  
En Blender, ve al panel MCP → Preferencias del complemento → campo `Auth Token`.

**Ejemplo de autenticación cliente:**
```json
{
    "type": "auth",
    "token": "mcp_secure_token_2026_victor"
}
```

> **Notas de seguridad:**  
> - Nunca publiques tu token.
> - Rótalo si habilitas modo LAN.
> - Usa tokens fuertes para múltiples máquinas.
> - El token es obligatorio incluso en modo local.

---
