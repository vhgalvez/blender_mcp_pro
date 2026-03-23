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
  - [Instalación](#instalación)
  - [Uso Seguro](#uso-seguro)
    - [Mismo PC](#mismo-pc)
    - [LAN (opcional)](#lan-opcional)
  - [Puente MCP STDIO](#puente-mcp-stdio)
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
│   ├── blender_client.py
│   └── mcp_adapter.py
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
- `client/blender_client.py`: Cliente TCP pequeño para autenticarse y enviar comandos al backend de Blender.
- `client/mcp_adapter.py`: Puente MCP por STDIO para clientes compatibles como Copilot/Codex.

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
- `create_character_blockout`
- `create_prop_blockout`
- `create_environment_layout`

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
