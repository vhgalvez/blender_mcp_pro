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
  - [Supported MCP Tools](#supported-mcp-tools)
  - [Character Workflow](#character-workflow)
  - [Environment Workflow](#environment-workflow)
  - [Multipurpose Usage](#multipurpose-usage)
  - [Client Directory Layout](#client-directory-layout)
  - [Instalación](#instalación)
  - [Uso Seguro](#uso-seguro)
    - [Mismo PC](#mismo-pc)
    - [LAN (opcional)](#lan-opcional)
  - [Puente MCP STDIO](#puente-mcp-stdio)
  - [Smoke Test](#smoke-test)
  - [How To Run From The Repository Root](#how-to-run-from-the-repository-root)
  - [End-to-End Test](#end-to-end-test)
  - [Troubleshooting](#troubleshooting)
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

6. Ejecuta el cliente o la CLI desde este repositorio:

```powershell
python client/smoke_test.py
python client/agent_cli.py
```

7. Usa `python client/smoke_test.py` para validar auth y comandos básicos.
8. Usa `python client/agent_cli.py` para prompts libres y llamadas raw.

---

## Architecture

El flujo actual queda así:

```text
VS Code / CLI / Local AI Agent
            |
            v
client/
(agent_cli.py, mcp_adapter.py, blender_client.py, smoke_test.py)
            |
            v
Blender TCP Server
(token-auth local socket)
            |
            v
blender_mcp_pro add-on
(addon.py, server.py, dispatcher.py, character_tools.py, integrations.py)
```

Responsabilidades:

- `blender_mcp_pro/` es lo único que se instala en Blender.
- `client/` permanece fuera de Blender y consume el servidor TCP autenticado.
- `client/blender_client.py` mantiene la compatibilidad con el cliente TCP actual.
- `client/agent_cli.py` y `client/mcp_adapter.py` ayudan a un agente local a usar herramientas reales del servidor sin cambiar la arquitectura del add-on.

---

## Supported MCP Tools

El toolkit local expone herramientas multipropósito agrupadas por dominio.

### Scene / Info

- `get_scene_info`
- `get_object_info`
- `get_viewport_screenshot`
- `get_telemetry_consent`
- `list_collections`:
  placeholder preparado para futuro. El backend actual todavía no expone colecciones.

### Character

- `load_character_references`
- `clear_character_references`
- `create_character_from_references`
- `create_character_blockout`
- `apply_character_symmetry`
- `build_character_hair`
- `build_character_face`
- `apply_character_materials`
- `capture_character_review`
- `compare_character_with_references`
- `apply_character_proportion_fixes`
- `review_and_fix_character`

### Props

- `create_prop_blockout`
- `apply_prop_symmetry`
- `apply_prop_materials`

### Environment / Layout

- `create_environment_layout`
- `apply_environment_materials`
- `create_shop_scene`
- `create_room_blockout`
- `create_street_blockout`

### Assets / Integrations

- `get_polyhaven_status`
- `get_hyper3d_status`
- `get_sketchfab_status`
- `get_hunyuan3d_status`
- `get_polyhaven_categories`
- `search_polyhaven_assets`
- `download_polyhaven_asset`
- `set_texture`
- `create_rodin_job`
- `poll_rodin_job_status`
- `import_generated_asset`
- `search_sketchfab_models`
- `get_sketchfab_model_preview`
- `download_sketchfab_model`
- `create_hunyuan_job`
- `poll_hunyuan_job_status`
- `import_generated_asset_hunyuan`

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

Esto cubre casos útiles como:

- room / bedroom blockouts
- shop / interior layouts

Importante:

- `create_street_blockout` no está implementado realmente en el servidor actual.
- si intentas usar un prompt de calle, el cliente devuelve `tool_not_implemented` y sugiere alternativas reales como `create_environment_layout` con `layout_type="corridor"`.

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

Lo que se instala en Blender:

- solo la carpeta `blender_mcp_pro/`

Lo que permanece fuera de Blender:

- toda la carpeta `client/`

No intentes instalar `client/` como add-on de Blender.

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

El backend real sigue siendo el add-on `blender_mcp_pro/` dentro de Blender:

- expone el servidor TCP local autenticado
- valida red y token
- ejecuta los comandos Blender en el hilo principal

El directorio `client/` es un consumidor externo de ese backend:

- `blender_client.py` habla el protocolo TCP actual
- `mcp_adapter.py` alinea prompts y tools con los comandos reales del servidor
- `agent_cli.py` ofrece una CLI práctica para workflows iterativos

La arquitectura correcta es:

```text
VS Code / CLI / Agent
        |
        v
client/
        |
        v
Blender TCP server
        |
        v
blender_mcp_pro/
```

`client/` no forma parte de la instalación del add-on.

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

Si este test pasa, el backend TCP, el token auth y las llamadas básicas funcionan.

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
- `crea un personaje punk`
- `create shop scene`
- `create bedroom blockout`
- `info de escena`
- `crea una mesa`
- `review the character`

---

## End-to-End Test

Pasos exactos para validar el flujo completo `cliente local -> client/ -> backend TCP de Blender -> cambio en escena`:

1. Inicia Blender.
2. Activa el complemento `Blender MCP`.
3. Abre el panel del complemento y pulsa `Start Server`.
4. En una terminal PowerShell, sitúate en este repositorio.
5. Define las variables de entorno que usa el cliente:

```powershell
$env:BLENDER_HOST = "127.0.0.1"
$env:BLENDER_PORT = "9876"
$env:BLENDER_TOKEN = "tu_token"
```

6. Lanza la CLI local:

```powershell
python client/agent_cli.py
```

7. Prueba prompts en inglés o español:

```text
scene info
info de escena
create a chair
crea una mesa
create shop scene
review character
revisa el personaje
```

Si todo está bien:

- la CLI devolverá el routing y el resultado en JSON
- Blender mostrará los cambios creados
- el token seguirá siendo obligatorio

Para depuración, el cliente escribe logs en `stderr`. Puedes subir el detalle con:

```powershell
$env:BLENDER_MCP_ADAPTER_LOG = "DEBUG"
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
