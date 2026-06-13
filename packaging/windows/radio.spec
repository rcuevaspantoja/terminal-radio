# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — onedir build (radio.exe + _internal/ + mpv/ sibling).
# Run: packaging/windows/build.ps1

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parents[1]
ENTRY = ROOT / "packaging" / "windows" / "_pyi_entry.py"

datas: list = []
hiddenimports: list = []
for package in ("textual", "rich", "pydantic", "pydantic_settings", "httpx", "httpcore", "h11"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    hiddenimports += pkg_hidden

block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports + [
        "terminal_radio",
        "terminal_radio.app",
        "terminal_radio.screens.main_screen",
        "terminal_radio.screens.theme_picker",
        "terminal_radio.screens.screensaver",
        "terminal_radio.screens.rename_modal",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="radio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TerminalRadio",
)
