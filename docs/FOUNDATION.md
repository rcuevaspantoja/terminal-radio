# Terminal Radio — Documento de fundamentos

> Versión: 0.1 · Estado: aprobado — distribución desktop en progreso
> Origen: [reverbic-cursor-brief.md](https://github.com/) + decisión de simplificar respecto a [Reverbic](https://github.com/sewandev/Reverbic)

---

## 1. Visión del producto

**Terminal Radio** es un reproductor de radio por internet en terminal, multiplataforma, enfocado en un único propósito: **buscar, guardar y escuchar estaciones de radio con una TUI clara y una instalación mínima**.

No es un port de Reverbic (Rust). Es una **reimplementación inspirada** en su experiencia visual y en el flujo de radio, descartando integraciones que complican el mantenimiento o limitan la plataforma (Spotify, YouTube, Discord, overlay flotante, detección de juegos).

### Principios de diseño (inmutables)

| # | Principio | Implicación |
|---|-----------|-------------|
| P1 | **Un propósito** | Solo radio por internet. Sin reproductores locales ni servicios de streaming propietarios. |
| P2 | **Misma experiencia en todas las plataformas** | Linux, Windows y macOS comparten código y flujo TUI; se recorta funcionalidad solo cuando el SO no la soporta. |
| P3 | **Instalación en 2–3 comandos** | En desarrollo: `python scripts/install.py`; para usuarios finales, releases desktop precompilados. |
| P4 | **TUI única** | Toda interacción ocurre en la terminal. Sin bandeja del sistema ni teclas multimedia globales. |
| P5 | **Dependencias opcionales nunca rompen** | `python-mpv` → try/except + fallback a subprocess; documentado en `--check`. |
| P6 | **Estado único** | Un solo `PlayerService` es la fuente de verdad; la UI solo observa y envía comandos. |

---

## 2. Alcance

### Incluido (MVP → v1.0)

| ID | Feature | Prioridad |
|----|---------|-----------|
| F-01 | Búsqueda de estaciones vía [radio-browser.info](https://www.radio-browser.info/) | MVP |
| F-02 | Reproducción de streams (play / pause / stop) | MVP |
| F-03 | Control de volumen | MVP |
| F-04 | Favoritos con renombrado | MVP |
| F-05 | Historial circular configurable | MVP |
| F-06 | Player bar (estación, track ICY, volumen) | MVP |
| F-07 | Screensaver (reloj + estación/track) | v1.0 |
| F-08 | Metadata enriquecida (Deezer → iTunes) | v1.0 |
| F-09 | Fuzzy search local en resultados | v1.0 |
| F-10 | Autoplay última estación | v1.0 |
| F-11 | `terminal-radio --check` (verificar dependencias) | v1.0 |

### Excluido (explícito, no reabrir sin decisión de producto)

- Spotify / librespot
- YouTube
- Discord Rich Presence
- Overlay flotante / game detection
- **Media keys globales** (teclas multimedia fuera de la terminal)
- **System tray** (icono en bandeja del SO)
- Crossfade entre estaciones (complejidad de audio; posible v2)
- macOS como target de primera clase *(ver decisión abierta D-02)*

---

## 3. Requisitos funcionales

### RF-01 — Búsqueda y catálogo

- RF-01.1: Al abrir la app, mostrar estaciones populares (`top_voted`) si no hay búsqueda activa.
- RF-01.2: Buscar por nombre con `/` + texto; llamada async a `/json/stations/search`.
- RF-01.3: Mostrar por ítem: nombre, codec, bitrate, país.
- RF-01.4: Registrar `click(uuid)` al reproducir (buena práctica con la API).
- RF-01.5: Rotar servidores API: `de1`, `nl1`, `at1` con `User-Agent: TerminalRadio/<version>`.
- RF-01.6: Errores de red → mensaje de una línea en TUI, sin stacktrace.

### RF-02 — Reproducción

- RF-02.1: Enter en estación → iniciar stream.
- RF-02.2: Space → play/pause; `q` → salir limpiamente (parar audio, guardar config).
- RF-02.3: `+` / `-` → volumen ±5 (configurable).
- RF-02.4: Mostrar `media-title` de ICY metadata cuando el stream lo provee.
- RF-02.5: Si `mpv` no está instalado → mensaje accionable con instrucciones por plataforma.

### RF-03 — Favoritos e historial

- RF-03.1: `f` → toggle favorito en estación seleccionada/reproduciendo.
- RF-03.2: `r` → modal de renombrado (Enter confirma, Esc cancela).
- RF-03.3: Historial: dedup por UUID, maxlen configurable, persistido entre sesiones.
- RF-03.4: Indicador ♥ en búsqueda si la estación ya es favorita.

### RF-04 — Screensaver

- RF-04.1: Activación manual con `l`; salida con cualquier tecla.
- RF-04.2: Activación automática tras `screensaver_idle_seconds` sin input.
- RF-04.3: Estación + pista actual centradas en pantalla.

### RF-05 — Configuración

- RF-05.1: Persistir en directorio estándar por OS (ver §6).
- RF-05.2: Override por env vars con prefijo `TERMINAL_RADIO_`.
- RF-05.3: Guardado automático en `on_unmount`.

---

## 4. Requisitos no funcionales

| ID | Requisito | Criterio |
|----|-----------|----------|
| RNF-01 | Arranque | TUI visible en < 2 s en hardware modesto |
| RNF-02 | Memoria | < 80 MB RAM en idle (sin contar mpv) |
| RNF-03 | Responsividad UI | Ninguna operación de red bloquea el event loop de Textual |
| RNF-04 | Portabilidad | Mismo entry point `terminal-radio` en las plataformas soportadas |
| RNF-05 | Recuperación | Fallo de stream → estado de error visible; app no crashea |
| RNF-06 | Accesibilidad instalación | README con bloques copy-paste por plataforma |
| RNF-07 | Testabilidad | Capas de dominio/servicio testeables sin TUI ni mpv real |

---

## 5. Casos de uso

### UC-1 — Primera reproducción (usuario nuevo)

**Actor:** Usuario sin experiencia en Python  
**Precondición:** `mpv` instalado  
**Flujo:** Instalar app → `terminal-radio` → `/` → "jazz" → Enter → flechas → Enter → escucha  
**Postcondición:** Estación en historial; volumen y config por defecto persistidos  

### UC-2 — Guardar y renombrar favorito

**Actor:** Usuario recurrente  
**Flujo:** Reproduciendo → `f` → tab Favorites → `r` → nuevo nombre → Enter  
**Postcondición:** `favorites.json` actualizado; nombre custom visible en Favorites  

### UC-4 — Sesión idle con screensaver

**Actor:** Usuario de escritorio  
**Flujo:** Reproducción activa → sin input N segundos → screensaver → cualquier tecla → vuelve  
**Postcondición:** Audio sigue sonando durante screensaver  

### UC-5 — Stream caído

**Actor:** Cualquiera  
**Flujo:** Estación deja de responder → mpv error → mensaje en player bar  
**Postcondición:** Usuario puede seleccionar otra estación sin reiniciar app  

---

## 6. Arquitectura

### 6.1 Vista por capas

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTACIÓN (Textual)                                 │
│  app.py · screens/ · widgets/                           │
│  Solo binding UI ↔ mensajes/comandos                    │
└──────────────────────────┬──────────────────────────────┘
                           │ PlayerMessage / callbacks
┌──────────────────────────▼──────────────────────────────┐
│  APLICACIÓN                                             │
│  services/player.py    — orquesta reproducción          │
│  services/station.py   — búsqueda, favoritos, historial│
└──────────────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────────┐
│ audio/        │  │ api/          │  │ data/ + config   │
│ AudioBackend  │  │ RadioBrowser  │  │ JSON persistido  │
│ factory       │  │ Metadata      │  │ pydantic-settings│
└───────────────┘  └───────────────┘  └──────────────────┘
        │
        ▼
┌───────────────┐
│ platform/     │  detect, deps, launcher
└───────────────┘
```

### 6.2 Componente central: `PlayerService`

Evita que `app.py` se convierta en un god object. Responsabilidades:

- Posee la instancia de `AudioBackend`
- Mantiene `PlayerState` (estación actual, volumen, playing, track_title, error)
- Notifica cambios vía callback/asyncio.Event o patrón observer simple
- Traduce comandos de UI: `play(station)`, `toggle_pause()`, `set_volume()`, `stop()`
- Dispara fetch de metadata enriquecida cuando cambia `track_title`

```python
# Contrato conceptual (no implementar aún)
class PlayerState(BaseModel):
    station: Station | None
    is_playing: bool
    volume: int  # 0-100
    track_title: str | None      # ICY / mpv media-title
    track_meta: TrackMeta | None # Deezer/iTunes
    error: str | None
```

### 6.3 Audio: estrategia por plataforma

```
create_audio_backend() → AudioBackend
│
├─ Windows                  → MpvSubprocessBackend (por defecto)
├─ Linux / macOS
│   ├─ python-mpv disponible → MpvBindingBackend
│   └─ else                  → MpvSubprocessBackend
└─ Error si mpv binary ausente en ambos caminos
```

**Interfaz `AudioBackend` (congelada):**

| Método | Descripción |
|--------|-------------|
| `play(url: str) -> None` | Inicia o cambia stream |
| `stop() -> None` | Detiene reproducción |
| `pause() -> None` | Pausa (si el stream lo permite) |
| `resume() -> None` | Reanuda |
| `set_volume(level: int) -> None` | 0–100 |
| `get_volume() -> int` | |
| `is_playing -> bool` | Property |
| `on_metadata(callback)` | Registra listener para `media-title` |
| `shutdown() -> None` | Limpieza al salir |

**IPC subprocess:** Unix socket `/tmp/terminal-radio-mpv.sock` · Windows pipe `\\.\pipe\terminal-radio-mpv`

### 6.4 Concurrencia (Textual + asyncio)

| Operación | Patrón |
|-----------|--------|
| HTTP (radio-browser, metadata) | `async def` + `httpx.AsyncClient` |
| Audio backend | Thread dedicado o callbacks de mpv; **nunca** bloquear el loop principal |
| Actualizar UI desde audio thread | `app.call_from_thread()` o `post_message()` de Textual |
| Polling metadata subprocess | Thread daemon, intervalo 3 s |

### 6.5 Flujo de datos: reproducir estación

```
User [Enter] → MainScreen
    → PlayerService.play(station)
        → AudioBackend.play(url)
        → HistoryStore.add(station)
        → RadioBrowserClient.click(uuid)  [async task]
        → UI actualiza PlayerBar
    ← AudioBackend.on_metadata(title)
        → PlayerService actualiza track_title
        → [async] MetadataService.fetch(title)
        → UI actualiza artista/álbum
```

---

## 7. Modelo de dominio

```
Station          — uuid, name, url, country, codec, bitrate, tags[]
FavoriteStation  — Station + custom_name: str | None
HistoryEntry     — station: Station, played_at: datetime
TrackMeta        — title, artist, album, artwork_url | None
AppSettings      — volume, history_max, screensaver_idle_seconds, ...
```

Todos los modelos en `models/` con Pydantic v2. Los stores (`data/`) serializan/deserializan estos tipos.

---

## 8. Estructura de archivos (v1 congelada)

```
terminal-radio/
├── pyproject.toml
├── README.md
├── scripts/
│   └── install.py
├── docs/
│   ├── FOUNDATION.md          ← este documento
│   └── screenshots/
└── terminal_radio/            ← paquete Python (snake_case)
    ├── __init__.py
    ├── __main__.py
    ├── app.py                 # Textual App; wiring fino
    ├── config.py
    ├── models/
    │   ├── station.py
    │   ├── player.py
    │   └── metadata.py
    ├── services/
    │   ├── player.py          # PlayerService
    │   └── metadata.py        # Orquesta enriquecimiento
    ├── audio/
    │   ├── backend.py         # ABC + factory
    │   ├── mpv_subprocess.py
    │   └── mpv_binding.py
    ├── api/
    │   ├── radio_browser.py
    │   └── metadata_providers.py  # Deezer + iTunes
    ├── data/
    │   ├── favorites.py
    │   └── history.py
    ├── screens/
    │   ├── main_screen.py
    │   ├── screensaver.py
    │   └── rename_modal.py
    ├── widgets/
    │   ├── player_bar.py
    │   └── station_list.py
    └── platform/
        ├── detect.py          # paths por plataforma
        ├── deps.py            # mpv y pip
        └── launcher.py        # shims radio / terminal-radio
```

**Cambio respecto al brief original:** se añade `models/`, `services/` y `widgets/` explícitos desde el día 1 para evitar refactor masivo después.

---

## 9. Persistencia

| OS | Directorio |
|----|------------|
| Linux / macOS | `~/.config/terminal-radio/` |
| Windows | `%APPDATA%\terminal-radio\` |

| Archivo | Contenido |
|---------|-----------|
| `config.json` | `AppSettings` |
| `favorites.json` | lista de `FavoriteStation` |
| `history.json` | lista de `HistoryEntry` |

Env prefix: `TERMINAL_RADIO_` (ej. `TERMINAL_RADIO_VOLUME=60`).

---

## 10. Stack técnico

| Rol | Librería | Notas |
|-----|----------|-------|
| TUI | textual ≥ 0.80 | Event loop asyncio |
| HTTP | httpx ≥ 0.27 | Solo async |
| Config | pydantic-settings ≥ 2.3 | |
| Audio binding | python-mpv ≥ 1.0.7 | Opcional |
| Audio binary | mpv | **Requisito externo obligatorio** |
| Fuzzy | rapidfuzz ≥ 3.9 | Pulido |
| Build | hatchling | Entry point: `terminal-radio` |
| Tooling dev | uv (recomendado) | |

Python: **3.11+**

---

## 11. Matriz de factibilidad por plataforma

| Capability | Linux desktop | Windows | macOS |
|------------|---------------|---------|-------|
| Textual TUI | ✅ | ✅ | ✅ |
| mpv subprocess | ✅ | ✅ | ✅ |
| python-mpv binding | ✅ si libmpv dev | ⚠️ requiere DLL de mpv instalado | ✅ si libmpv está disponible |
| radio-browser API | ✅ | ✅ | ✅ |
| Deezer/iTunes API | ✅ | ✅ | ✅ |
| Atajos TUI (Space, q, l, …) | ✅ | ✅ | ✅ |
| Instalación de desarrollo | `install.py` | `install.py` | `install.py` |

### Riesgos identificados

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| `python-mpv` sin libmpv en PATH (Windows) | Media | Fallback automático a subprocess; `--check` documenta |
| Streams muertos / timeouts | Alta | Timeout en play; mensaje UI; no crashear |
| Textual + threads audio | Media | `call_from_thread` siempre; pruebas manuales tempranas |
| Tamaño terminal pequeño | Baja | Layout responsive mínimo; probar en 80×24 |
| API radio-browser caída | Media | Rotación de servidores + retry 1 vez |

---

## 12. Plan de fases (validado)

| Fase | Entregable | Criterio de done |
|------|------------|------------------|
| **0** | Esqueleto + config + TUI vacía | `uv run terminal-radio` muestra header, `q` sale |
| **1** | Audio backends + factory | Stream hardcodeado reproduce en ≥2 plataformas |
| **2** | Búsqueda + MainScreen + PlayerBar | Flujo buscar→reproducir end-to-end |
| **3** | Favoritos + historial + rename | Persistencia entre sesiones |
| **4** | Lock screen + metadata | Idle timer + artista en barra |
| **5** | Distribución desktop | Releases precompilados para Windows y Linux |

### 12.1 Fase 5 — Distribución desktop (detalle)

**Objetivo:** el usuario final **no** clona el repo ni ejecuta `install.py` (pip, venv, Scoop, etc.). La app se empaqueta en **CI**; en local solo descarga y ejecuta.

| Plataforma | Formato | Experiencia usuario |
|------------|---------|---------------------|
| **Windows** | Instalador (Inno Setup / MSI) + zip portable | Descargar → instalar o descomprimir → `Radio` desde menú o acceso directo |
| **Linux** | Release `.tar.gz` o AppImage (x86_64) | Descargar → `./radio` (mpv documentado o incluido) |

**Build:** GitHub Actions en cada tag — PyInstaller (o venv embebido) + **mpv portable** en Windows.

**Audiencias:**

| Quién | Camino |
|-------|--------|
| Usuario final | Release precompilado |
| Desarrollador | `pip install -e ".[dev]"` (sin script largo) |

**Dependencia externa:** `mpv` — en Windows se incluye en el instalador; en Linux, empaquetado o un paso mínimo (`apt install mpv`).

**Opcional post–v1.0:** PyPI + `pipx`, `winget`, `.deb` / Flatpak.

---

## 13. Decisiones cerradas

| ID | Decisión |
|----|----------|
| **D-01** | Stack: **Python 3.11+**. CLI: **`terminal-radio`** |
| **D-02** | macOS: *best-effort* (mismo código que Linux), sin CI dedicado inicial |
| **D-03** | Metadata enriquecida en **v1.0 (Fase 4)**; MVP solo título ICY |
| **D-04** | **Sin** media keys ni system tray — excluido del producto (P4) |
| **D-05** | Licencia: **MIT** |
| **D-06** | Tests mínimos desde Fase 0: `detect`, `config` |

---

## 14. Próximo paso

**Fase 5 (prioridad)** — releases desktop: Windows (instalador Inno Setup) + Linux (tarball/AppImage); CI en GitHub Actions.

**Instalador dev** — `scripts/install.py` queda para desarrollo; no es la vía del usuario final.
