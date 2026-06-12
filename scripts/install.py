#!/usr/bin/env python3
"""
Instalador multiplataforma de Terminal Radio.

Mismo comando en Linux, Windows, macOS y Termux:

    python scripts/install.py

Instala mpv (si falta) con el gestor de paquetes nativo del SO y luego
la aplicación en un venv cuando el SO lo exige (PEP 668).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _bootstrap_path() -> None:
    """Permite importar terminal_radio sin pip install previo."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def install_app(editable: bool = True) -> tuple[bool, Path, Path]:
    """
    Instala terminal-radio con pip.

    Devuelve (exito, python_a_usar, directorio_del_venv).
    """
    from terminal_radio.platform.deps import (
        default_venv_dir,
        ensure_termux_python_wheels,
        ensure_venv,
        is_externally_managed,
        is_termux,
        print_termux_pip_failure_hint,
        termux_pip_extra_index_args,
    )

    python = Path(sys.executable)
    venv_dir = default_venv_dir(REPO_ROOT)
    used_venv = False

    if is_externally_managed():
        print("\n-> Python gestionado por el SO (PEP 668); se usara un venv")
        try:
            python = ensure_venv(venv_dir, repo_root=REPO_ROOT)
            used_venv = True
        except RuntimeError as exc:
            print(f"  [error] {exc}")
            return False, Path(sys.executable), venv_dir

    if is_termux() and not ensure_termux_python_wheels(python):
        return False, python, venv_dir

    cmd = [str(python), "-m", "pip", "install", *termux_pip_extra_index_args()]
    if editable:
        cmd.append("-e")
    cmd.append(str(REPO_ROOT))
    print("\n-> Instalar Terminal Radio")
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("  [error] Fallo la instalacion de la app")
        if is_termux():
            print_termux_pip_failure_hint()
        return False, python, venv_dir
    print("  [ok] Terminal Radio instalado")
    if used_venv:
        print(f"  python del venv: {python}")

    from terminal_radio.platform.launcher import install_cli_shims, local_bin_install_hint

    shims, path_modified = install_cli_shims(python, venv_dir if used_venv else None)
    print("\n-> Comandos globales instalados:")
    for shim in shims:
        print(f"  {shim}")
    if path_modified:
        print("\n[ok] PATH de usuario actualizado (%USERPROFILE%\\.local\\bin)")
    hint = local_bin_install_hint(shims[0].parent, path_modified=path_modified)
    if hint:
        print(f"\n[aviso] {hint}")

    return True, python, venv_dir


def _print_run_instructions(_python: Path, _venv_dir: Path, used_venv: bool) -> None:
    print("\n" + "=" * 40)
    print("Listo. Ejecuta desde cualquier directorio:")
    print("  radio")
    print("  # o: terminal-radio")
    if used_venv:
        print("\n  (No necesitas source ni activar el venv.)")


def main(argv: list[str] | None = None) -> int:
    _bootstrap_path()
    from terminal_radio.platform.deps import (
        check_report,
        default_venv_dir,
        ensure_mpv,
        ensure_pip,
        is_externally_managed,
        is_repo_on_windows_mount,
        mpv_available,
        pip_available,
        python_version_ok,
    )

    parser = argparse.ArgumentParser(
        description="Instala dependencias y Terminal Radio (multiplataforma).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Solo muestra el estado de dependencias, no instala nada.",
    )
    parser.add_argument(
        "--skip-mpv",
        action="store_true",
        help="No intentar instalar mpv.",
    )
    parser.add_argument(
        "--skip-app",
        action="store_true",
        help="No instalar la aplicación con pip.",
    )
    parser.add_argument(
        "--no-editable",
        action="store_true",
        help="pip install sin modo editable (para empaquetado).",
    )
    args = parser.parse_args(argv)

    print("Terminal Radio — instalador")
    print("=" * 40)

    if not python_version_ok():
        print(f"[error] Python {sys.version_info.major}.{sys.version_info.minor} detectado.")
        print("  Se requiere Python 3.11 o superior.")
        return 1

    if args.check_only:
        print(check_report())
        if is_externally_managed():
            venv_dir = default_venv_dir(REPO_ROOT)
            print("\nNota: este SO requiere venv para instalar la app con pip.")
            print(f"  venv previsto: {venv_dir}")
        if is_repo_on_windows_mount(REPO_ROOT):
            print("\nNota: repo en /mnt/ (WSL). El venv no puede vivir junto al codigo en Windows.")
        ok = python_version_ok() and pip_available() and mpv_available()
        return 0 if ok else 1

    if not args.skip_mpv:
        if mpv_available():
            print("[ok] mpv ya esta instalado")
        elif not ensure_mpv():
            return 1
    elif not mpv_available():
        print("[aviso] mpv no encontrado (--skip-mpv activo)")

    used_venv = False
    run_python = Path(sys.executable)
    venv_dir = default_venv_dir(REPO_ROOT)

    if not args.skip_app:
        if not pip_available() and not ensure_pip():
            return 1
        ok, run_python, venv_dir = install_app(editable=not args.no_editable)
        if not ok:
            return 1
        used_venv = is_externally_managed()

    _print_run_instructions(run_python, venv_dir, used_venv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
