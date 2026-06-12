#!/usr/bin/env python3
"""
Instalador Termux para Terminal Radio.

Instala dependencias de runtime con pip (wheels precompilados) y registra
`radio` / `terminal-radio` apuntando al checkout con PYTHONPATH.
No ejecuta `pip install .` del proyecto (evita hatchling/editables en Android).

    python scripts/install-termux.py
    sh scripts/install-termux.sh
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _bootstrap_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    _bootstrap_path()
    from terminal_radio.platform.deps import (
        ensure_mpv,
        ensure_pip,
        ensure_termux_app_dependencies,
        is_termux,
        mpv_available,
        pip_available,
        python_version_ok,
    )
    from terminal_radio.platform.launcher import (
        get_local_bin_dir,
        install_termux_cli_shims,
        local_bin_install_hint,
    )

    print("Terminal Radio — instalador Termux")
    print("=" * 40)

    if not is_termux():
        print("[error] Este script solo funciona en Termux (Android).")
        print("  En otros sistemas usa: python scripts/install.py")
        return 1

    if not python_version_ok():
        print("[error] Se requiere Python 3.11 o superior.")
        return 1

    python = Path(sys.executable)

    if not pip_available() and not ensure_pip():
        return 1

    if mpv_available():
        print("[ok] mpv ya esta instalado")
    elif not ensure_mpv():
        return 1

    if not ensure_termux_app_dependencies(python):
        return 1

    shims = install_termux_cli_shims(python, REPO_ROOT)
    print("\n-> Comandos instalados (PYTHONPATH -> repo):")
    for shim in shims:
        print(f"  {shim}")

    hint = local_bin_install_hint(shims[0].parent)
    if hint:
        print(f"\n[aviso] {hint}")

    print("\n" + "=" * 40)
    print("Listo. Ejecuta:")
    print("  radio")
    print("\nActualizar tras git pull: python scripts/install-termux.py")
    print("\nCuando exista el paquete TUR: pkg install terminal-radio")

    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [str(python), "-c", "import terminal_radio; print(terminal_radio.__version__)"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("\n[aviso] Import de prueba fallo; revisa dependencias pip arriba.")
        if result.stderr:
            print(result.stderr.strip())
    else:
        print(f"\n[ok] Import OK (v{result.stdout.strip()})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
