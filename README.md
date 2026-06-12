# Terminal Radio

Reproductor de radio por internet en terminal para **Linux**, **Windows**, **macOS** y **Termux (Android)**.

Inspirado en [Reverbic](https://github.com/sewandev/Reverbic), enfocado solo en radio: búsqueda, favoritos, historial y reproducción vía `mpv`.

## Instalación (todas las plataformas)

Mismo flujo en cualquier SO: clonar el repo y ejecutar el instalador. Detecta la plataforma y usa el gestor de paquetes nativo para `mpv`.

### Requisitos previos

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **pip** — en Ubuntu/WSL: `sudo apt install python3-pip` (el instalador lo hace solo si falta)
- En Ubuntu 23.04+ el instalador crea un **venv** automáticamente (PEP 668)
- **WSL** con repo en `/mnt/c/...`: el venv va a `~/.local/share/terminal-radio/venv` (no se puede crear en el disco Windows)

### Un comando

```bash
git clone <repo-url> terminal-radio
cd terminal-radio
python scripts/install.py
```

En **Windows (PowerShell)** — recomendado (añade `radio` al PATH de usuario y de la sesión actual):

```powershell
git clone <repo-url> terminal-radio
cd terminal-radio
.\scripts\install.ps1
```

Equivalente con Python directo:

```powershell
python scripts/install.py
```

Tras instalar en Windows: escribe `radio` en esa misma ventana. En **terminales nuevas**, `radio` también funciona (el instalador registra `%USERPROFILE%\.local\bin` en el PATH del usuario).

En Linux/macOS/Termux también puedes usar:

```bash
./scripts/install.sh
```

### Qué hace el instalador

1. Comprueba Python 3.11+
2. Si falta **mpv**, lo instala con el gestor detectado:

| Plataforma | Gestor (en orden de preferencia) |
|------------|----------------------------------|
| Windows | **Scoop** (extras/mpv) → Chocolatey → winget portable *(solo sin Scoop)* |
| Debian/Ubuntu / WSL | `sudo apt update && sudo apt install mpv` — si no existe el paquete: `sudo snap install mpv` |
| Fedora/RHEL | `sudo dnf install mpv` |
| Arch | `sudo pacman -S mpv` |
| openSUSE | `sudo zypper install mpv` |
| Alpine | `sudo apk add mpv` |
| Termux | `pkg install mpv` |
| macOS | `brew install mpv` |

3. Instala Terminal Radio con `pip install -e .`

No instala Scoop, Homebrew ni otros gestores automáticamente — solo usa los que ya tienes en el sistema.

### Verificar sin instalar

```bash
python scripts/install.py --check-only
terminal-radio --check
```

### Opciones del instalador

```bash
python scripts/install.py --check-only   # solo informe
python scripts/install.py --skip-mpv     # solo la app Python
python scripts/install.py --skip-app     # solo mpv
```

## Uso

Tras `python scripts/install.py`, usa **un solo comando** (sin `source`, sin rutas):

```bash
radio
```

También funciona `terminal-radio`. El instalador registra ambos en `~/.local/bin` (Linux/macOS/WSL) o `%USERPROFILE%\.local\bin` (Windows).

```bash
radio --version
radio --check
```

| Plataforma | Si `radio` no se encuentra |
|------------|----------------------------|
| Linux | Añade `~/.local/bin` al PATH (el instalador te lo indica) |
| Windows | Usa `.\scripts\install.ps1` o reabre la terminal tras `install.py` |

Atajos actuales (Fase 1):

| Tecla | Acción |
|-------|--------|
| `p` | Reproducir stream de prueba (SomaFM Groove Salad) |
| `Space` | Pausar / reanudar |
| `s` | Detener |
| `+` / `-` | Subir / bajar volumen |
| `q` | Salir |

## Configuración

Archivos en:

- Linux / Termux / macOS: `~/.config/terminal-radio/`
- Windows: `%APPDATA%\terminal-radio\`

Variables de entorno (prefijo `TERMINAL_RADIO_`):

```bash
TERMINAL_RADIO_VOLUME=60
TERMINAL_RADIO_AUTOPLAY_LAST=true
```

## Desarrollo

```bash
pip install -e ".[dev]"
python -m pytest
```

Documento de arquitectura: [docs/FOUNDATION.md](docs/FOUNDATION.md).

## ¿Qué es mpv?

[mpv](https://mpv.io/) es el reproductor de audio que usa Terminal Radio por debajo. La app no decodifica streams ella misma; controla `mpv` como motor. Es una dependencia de sistema (como `git`), no una librería Python.

**Windows:** evita `winget install shinchiro.mpv` — instala una app GUI ("MPV Player") que no deja `mpv.exe` en PATH. El instalador usa Scoop (`scoop install mpv`) cuando está disponible.

Si mpv está instalado pero no en PATH, define la ruta manualmente:

```powershell
set TERMINAL_RADIO_MPV=C:\Users\tu\scoop\apps\mpv\current\mpv.exe
```

## Estado

**Fase 1** — audio funcional vía mpv (subprocess + binding opcional).

## Licencia

MIT
