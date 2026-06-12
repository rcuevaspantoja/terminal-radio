# Terminal Radio — Documento de fundamentos

> Versión: 0.1 · Estado: aprobado — Fase 0 en progreso  
> Origen: [reverbic-cursor-brief.md](https://github.com/) + decisión de simplificar respecto a [Reverbic](https://github.com/sewandev/Reverbic)

---

## 1. Visión del producto

**Terminal Radio** es un reproductor de radio por internet en terminal, multiplataforma, enfocado en un único propósito: **buscar, guardar y escuchar estaciones de radio con una TUI clara y una instalación mínima**.

No es un port de Reverbic (Rust). Es una **reimplementación inspirada** en su experiencia visual y en el flujo de radio, descartando integraciones que complican el mantenimiento o limitan la plataforma (Spotify, YouTube, Discord, overlay flotante, detección de juegos).

### Principios de diseño (inmutables)

| # | Principio | Implicación |
|---|-----------|-------------|
| P1 | **Un propósito** | Solo radio por internet. Sin reproductores locales ni servicios de streaming propietarios. |
| P2 | **Multiplataforma real** | Linux, Windows y Termux (Android) con el mismo código y degradación elegante de features opcionales. |
| P3 | **Instalación en 2–3 comandos** | `python scripts/install.py` (mismo comando en todos los SO). Instala `mpv` vía gestor nativo + la app con pip. |
| P4 | **TUI primero** | La terminal es la interfaz principal; tray y media keys son complementos, no requisitos. |
| P5 | **Dependencias opcionales nunca rompen** | `pynput`, `pystray`, `python-mpv` → try/except + fallback documentado. |
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
| F-09 | Media keys globales | v1.0 |
| F-10 | Icono en system tray | v1.0 |
| F-11 | Fuzzy search local en resultados | v1.0 |
| F-12 | Autoplay última estación | v1.0 |
| F-13 | `terminal-radio --check` (verificar dependencias) | v1.0 |

### Excluido (explícito, no reabrir sin decisión de producto)

- Spotify / librespot
- YouTube
- Discord Rich Presence
- Overlay flotante / game detection
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

- RF-04.1: Activación manual con `s`; salida con cualquier tecla.
- RF-04.2: Activación automática tras `screensaver_idle_seconds` sin input.
- RF-04.3: Reloj en caracteres de bloque + estación + track actual.

### RF-05 — Integraciones de plataforma

- RF-05.1: Media keys (play/pause, stop, next) en Linux/Windows vía `pynput`.
- RF-05.2: System tray con menú Show / Play-Pause / Stop / Quit.
- RF-05.3: En Termux: omitir silenciosamente RF-05.1 y RF-05.2.

### RF-06 — Configuración

- RF-06.1: Persistir en directorio estándar por OS (ver §6).
- RF-06.2: Override por env vars con prefijo `TERMINAL_RADIO_`.
- RF-06.3: Guardado automático en `on_unmount`.

---

## 4. Requisitos no funcionales

| ID | Requisito | Criterio |
|----|-----------|----------|
| RNF-01 | Arranque | TUI visible en < 2 s en hardware modesto |
| RNF-02 | Memoria | < 80 MB RAM en idle (sin contar mpv) |
| RNF-03 | Responsividad UI | Ninguna operación de red bloquea el event loop de Textual |
| RNF-04 | Portabilidad | Mismo entry point `terminal-radio` en las 3 plataformas |
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

### UC-3 — Radio en Termux (smartphone)

**Actor:** Usuario móvil  
**Flujo:** `pkg install mpv python` → `pip install terminal-radio` → `terminal-radio`  
**Postcondición:** TUI funcional; sin tray ni media keys; audio vía subprocess mpv  

### UC-4 — Sesión idle con screensaver

**Actor:** Usuario de escritorio  
**Flujo:** Reproducción activa → sin input N segundos → screensaver → cualquier tecla → vuelve  
**Postcondición:** Audio sigue sonando durante screensaver  

### UC-5 — Control desde el SO (Linux/Windows)

**Actor:** Usuario de escritorio  
**Flujo:** Minimiza terminal → media key pause → tray muestra estación → Stop desde menú  
**Postcondición:** Audio detenido sin reabrir terminal  

### UC-6 — Stream caído

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
│ platform/     │  (media_keys, tray — opcional)
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
├─ Termux ($PREFIX set)     → MpvSubprocessBackend (siempre)
├─ Linux / Windows
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
├── docs/
│   └── FOUNDATION.md          ← este documento
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
        ├── detect.py          # is_termux(), paths
        ├── media_keys.py
        └── tray.py
```

**Cambio respecto al brief original:** se añade `models/`, `services/` y `widgets/` explícitos desde el día 1 para evitar refactor masivo después.

---

## 9. Persistencia

| OS | Directorio |
|----|------------|
| Linux / Termux | `~/.config/terminal-radio/` |
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
| Media keys | pynput ≥ 1.7.7 | Opcional |
| Tray | pystray + Pillow | Opcional |
| Fuzzy | rapidfuzz ≥ 3.9 | Fase 6 |
| Build | hatchling | Entry point: `terminal-radio` |
| Tooling dev | uv (recomendado) | |

Python: **3.11+**

---

## 11. Matriz de factibilidad por plataforma

| Capability | Linux desktop | Windows | Termux |
|------------|---------------|---------|--------|
| Textual TUI | ✅ | ✅ | ✅ (terminal local) |
| mpv subprocess | ✅ | ✅ | ✅ (`pkg install mpv`) |
| python-mpv binding | ✅ si libmpv dev | ⚠️ requiere DLL de mpv instalado | ❌ no usar |
| radio-browser API | ✅ | ✅ | ✅ |
| Deezer/iTunes API | ✅ | ✅ | ✅ |
| pynput media keys | ⚠️ X11/Wayland | ✅ | ❌ omitir |
| pystray | ✅ (necesita tray) | ✅ | ❌ omitir |
| Instalación pip/uv | ✅ | ✅ | ✅ |

### Riesgos identificados

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| `python-mpv` sin libmpv en PATH (Windows) | Media | Fallback automático a subprocess; `--check` documenta |
| pynput en Wayland Linux | Media | Degradar silencioso; documentar limitación |
| Streams muertos / timeouts | Alta | Timeout en play; mensaje UI; no crashear |
| Textual + threads audio | Media | `call_from_thread` siempre; pruebas manuales tempranas |
| Tamaño terminal pequeño (Termux) | Baja | Layout responsive mínimo; probar en 80×24 |
| API radio-browser caída | Media | Rotación de servidores + retry 1 vez |

---

## 12. Plan de fases (validado)

| Fase | Entregable | Criterio de done |
|------|------------|------------------|
| **0** | Esqueleto + config + TUI vacía | `uv run terminal-radio` muestra header, `q` sale |
| **1** | Audio backends + factory | Stream hardcodeado reproduce en ≥2 plataformas |
| **2** | Búsqueda + MainScreen + PlayerBar | Flujo buscar→reproducir end-to-end |
| **3** | Favoritos + historial + rename | Persistencia entre sesiones |
| **4** | Screensaver + metadata | Idle timer + artista en barra |
| **5** | Media keys + tray | Funciona Linux/Win; no-op Termux |
| **6** | Pulido + `--check` + distribución | README copy-paste; pipx/uv tool |

---

## 13. Decisiones cerradas

| ID | Decisión |
|----|----------|
| **D-01** | Stack: **Python 3.11+**. CLI: **`terminal-radio`** |
| **D-02** | macOS: *best-effort* (mismo código que Linux), sin CI dedicado inicial |
| **D-03** | Metadata enriquecida en **v1.0 (Fase 4)**; MVP solo título ICY |
| **D-04** | Tray/media keys en **Fase 5**, después del core estable |
| **D-05** | Licencia: **MIT** |
| **D-06** | Tests mínimos desde Fase 0: `detect`, `config` |

---

## 14. Próximo paso

**Fase 3** — favoritos (`f`), renombrar (`r`), historial con dedup y persistencia JSON.

**Fase 4** — screensaver + metadata enriquecida en la barra de reproducción.
