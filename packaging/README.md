# Packaging (Phase 6)

Pre-built releases for end users. Developers still use `pip install -e ".[dev]"`.

## Windows

**Output:** `dist/TerminalRadio/` (folder) and `dist/TerminalRadio-win64.zip`.

**Requirements:** Python 3.11+, pip. Optional: [Inno Setup 6](https://jrsoftware.org/isinfo.php) for `.exe` installer.

```powershell
# From repo root
.\packaging\windows\build.ps1 -DownloadMpv

# With installer (Inno Setup must be installed)
.\packaging\windows\build.ps1 -DownloadMpv -BuildInstaller
```

Layout after build:

```
dist/TerminalRadio/
  radio.exe
  terminal-radio.exe
  mpv/mpv.exe          # when -DownloadMpv or copied manually
  _internal/           # PyInstaller deps
```

The app finds bundled `mpv\mpv.exe` automatically; no Scoop or PATH needed.

**CI:** pushing a tag `v*` runs `.github/workflows/release-windows.yml` and attaches the zip to GitHub Releases.

## Linux

Planned: tarball / AppImage (see `docs/FOUNDATION.md` §12.2).
