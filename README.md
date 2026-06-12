# Terminal Radio

Internet radio player for your terminal. Works on **Linux**, **Windows**, **macOS**, and **Termux (Android)**.

Search stations, save favorites, keep a play history, and listen through [mpv](https://mpv.io/). Inspired by [Reverbic](https://github.com/sewandev/Reverbic), focused on radio only.

---

## Quick start

```bash
git clone <repo-url> terminal-radio
cd terminal-radio
python scripts/install.py
radio
```

On **Windows (PowerShell)**, use the wrapper script (updates PATH for the current session):

```powershell
git clone <repo-url> terminal-radio
cd terminal-radio
.\scripts\install.ps1
radio
```

---

## Features

- **Search** — popular stations on startup; search by name with `/`
- **Favorites** — save stations and rename them (`f`, `r`)
- **History** — recently played (deduplicated)
- **Player bar** — station name + track/artist (ICY metadata + Deezer/iTunes lookup)
- **Lock** — full-screen view with station and song (`l`, or auto after idle)
- **Themes** — switch color themes with live preview (`t`)

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Python 3.11+** | [python.org](https://www.python.org/downloads/) |
| **pip** | Usually bundled with Python |
| **mpv** | Audio engine (installed by the script if missing) |

On Ubuntu 23.04+ and similar distros, the installer creates a **venv** automatically (PEP 668).

**WSL** with the repo under `/mnt/c/...`: the venv lives at `~/.local/share/terminal-radio/venv` (cannot sit on the Windows mount).

### Termux (Android)

**Recommended (when published to TUR):**

```bash
pkg install tur-repo    # once, if needed
pkg install terminal-radio
radio
```

**Until the `.deb` is on TUR** — install from a git checkout (no `pip install .`; avoids build failures on Android):

```bash
pkg update && pkg upgrade
pkg install python python-pip mpv git
git clone <repo-url> terminal-radio
cd terminal-radio
./scripts/install-termux.sh
radio
```

The Termux script installs runtime dependencies from [TUR PyPI](https://termux-user-repository.github.io/pypi/) / [Eutalix](https://eutalix.github.io/android-pydantic-core/) and registers `radio` with `PYTHONPATH` pointing at the repo. Same TUI and shortcuts as desktop.

After `git pull`, re-run `./scripts/install-termux.sh` if dependencies change.

Do **not** run `pip install --upgrade pip` on Termux — it breaks the `python-pip` package.

Packaging recipe for maintainers: [tur/README.md](tur/README.md).

---

## Installation

All platforms use the same Python installer. The `.ps1` / `.sh` scripts are shortcuts.

| Platform | Command |
|----------|---------|
| Any | `python scripts/install.py` |
| Windows | `.\scripts\install.ps1` |
| Linux / macOS | `./scripts/install.sh` |
| Termux | `./scripts/install-termux.sh` |

### What the installer does

1. Checks Python 3.11+
2. Installs **mpv** if needed (via your system package manager)
3. Installs Terminal Radio with `pip install -e .`
4. Registers **`radio`** and **`terminal-radio`** in your user bin folder

| OS | Commands installed to |
|----|------------------------|
| Linux / macOS / WSL | `~/.local/bin` |
| Windows | `%USERPROFILE%\.local\bin` |

After install, run `radio` from any directory. On Windows, **new terminals** pick up PATH automatically; `install.ps1` also updates the current session.

### mpv by platform

| Platform | Package manager (first match wins) |
|----------|-----------------------------------|
| Windows | Scoop → Chocolatey → winget portable |
| Debian / Ubuntu / WSL | `apt` → `snap` fallback |
| Fedora / RHEL | `dnf` |
| Arch | `pacman` |
| openSUSE | `zypper` |
| Alpine | `apk` |
| Termux | `pkg` |
| macOS | Homebrew |

The installer does **not** install Scoop, Homebrew, etc. — it only uses what you already have.

### Installer options

```bash
python scripts/install.py --check-only   # report only, no install
python scripts/install.py --skip-mpv     # app only
python scripts/install.py --skip-app       # mpv only
python scripts/install.py --no-editable    # non-editable pip install
```

### Verify

```bash
python scripts/install.py --check-only
radio --check
radio --version
```

---

## Usage

```bash
radio
```

### Tabs

| Tab | Description |
|-----|-------------|
| **Search** | Popular stations on launch; `/` to search |
| **Favorites** | Saved stations (`f` to toggle) |
| **History** | Recent plays |

Use arrow keys to select, then **Enter** or **p** to play. Double-click also works.

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `/` | Search |
| `Enter` / `p` | Play selected station |
| `Space` | Pause / resume |
| `+` / `-` | Volume up / down (meter shows briefly) |
| `f` | Add / remove favorite |
| `r` | Rename favorite (Favorites tab) |
| `l` | Lock — full-screen station + song |
| `t` | Theme picker (live preview) |
| `q` | Quit |
| `Esc` | Cancel search |

On **Favorites** and **History**, the footer hides Search/Quit hints to reduce clutter; the keys still work.

### Lock screen

- Press **`l`** anytime, or wait for idle timeout (default **120 s**)
- Shows station name and current track
- **Any key** returns to the app
- Audio **keeps playing**

To disable auto-lock: set `"screensaver_idle_seconds": 0` in `config.json`.

---

## Configuration

Data directory:

| OS | Path |
|----|------|
| Linux / macOS / Termux | `~/.config/terminal-radio/` |
| Windows | `%APPDATA%\terminal-radio\` |

| File | Contents |
|------|----------|
| `config.json` | Volume, idle timeout, history size, … |
| `favorites.json` | Favorites and custom names |
| `history.json` | Play history |

Environment overrides (prefix `TERMINAL_RADIO_`):

```bash
TERMINAL_RADIO_VOLUME=60
TERMINAL_RADIO_HISTORY_MAX=100
TERMINAL_RADIO_SCREENSAVER_IDLE_SECONDS=30
TERMINAL_RADIO_AUTOPLAY_LAST=true
```

### Windows: mpv tips

Avoid `winget install shinchiro.mpv` — it installs a **GUI app** that does not put `mpv.exe` on PATH.

Recommended:

```powershell
scoop bucket add extras
scoop install mpv
```

If mpv is installed but not detected:

```powershell
$env:TERMINAL_RADIO_MPV = "C:\Users\you\scoop\apps\mpv\current\mpv.exe"
```

### Diagnostics

```bash
radio --perf          # performance log in the config directory
# F12 in-app saves a report when --perf is active
```

---

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```

Architecture and roadmap: [docs/FOUNDATION.md](docs/FOUNDATION.md).

---

## Project status

| Phase | Status |
|-------|--------|
| Audio (mpv) | Done |
| Search + UI | Done |
| Favorites + history | Done |
| Lock + track metadata | Done |
| Termux distribution (TUR `.deb`) | In progress |
| Polish + desktop distribution | Planned |

## License

MIT
