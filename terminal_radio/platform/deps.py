"""Comprobación e instalación de dependencias del sistema."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from terminal_radio.platform.detect import is_termux

ENV_MPV_OVERRIDE = "TERMINAL_RADIO_MPV"

# winget shinchiro.mpv instala "MPV Player" (GUI, Inno Setup) y NO expone mpv.exe
# en PATH. No usarlo en instalación automática.
_WINGET_GUI_PACKAGE = "shinchiro.mpv"

_WIN_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class LinuxFamily(str, Enum):
    DEBIAN = "debian"
    FEDORA = "fedora"
    ARCH = "arch"
    SUSE = "suse"
    ALPINE = "alpine"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InstallStep:
    """Un paso de instalación con descripción y comando."""

    description: str
    command: list[str]
    shell: bool = False
    verify_mpv: bool = True


def _is_rejected_windows_mpv(path: Path) -> bool:
    """Instaladores GUI (p. ej. winget shinchiro.mpv) no sirven como motor CLI."""
    text = str(path).lower()
    return "mpv player" in text or "shinchiro" in text


def _verify_mpv_cli(path: Path) -> bool:
    """Comprueba que el binario responde como mpv CLI (no un launcher GUI)."""
    if not path.is_file():
        return False
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            timeout=8,
            creationflags=_WIN_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    output = (result.stdout or b"") + (result.stderr or b"")
    return b"mpv" in output.lower()


def _windows_mpv_search_paths() -> list[Path]:
    """Rutas candidatas en orden de preferencia (Scoop CLI primero)."""
    home = Path.home()
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    paths: list[Path] = []

    scoop_root = home / "scoop" / "apps" / "mpv"
    if scoop_root.is_dir():
        current = scoop_root / "current" / "mpv.exe"
        if current.is_file():
            paths.append(current)
        for version_dir in sorted(scoop_root.iterdir(), reverse=True):
            if version_dir.name == "current":
                continue
            candidate = version_dir / "mpv.exe"
            if candidate.is_file():
                paths.append(candidate)

    shim = home / "scoop" / "shims" / "mpv.exe"
    if shim.is_file():
        paths.append(shim)

    paths.append(program_files / "mpv" / "mpv.exe")
    paths.extend(_winget_mpv_candidates())

    which = shutil.which("mpv")
    if which:
        paths.append(Path(which))

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in paths:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def find_rejected_mpv_installs() -> list[str]:
    """Instalaciones detectadas que no deben usarse (solo informativo)."""
    if sys.platform != "win32":
        return []
    home = Path.home()
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    suspects = [
        program_files / "MPV Player" / "mpv.exe",
        home / "AppData" / "Local" / "Programs" / "MPV Player" / "mpv.exe",
    ]
    found: list[str] = []
    for path in suspects:
        if path.is_file():
            found.append(str(path.resolve()))
    return found


def _linux_known_paths() -> list[Path]:
    """Rutas habituales de mpv en Linux (snap, etc.)."""
    return [
        Path("/snap/bin/mpv"),
        Path("/usr/bin/mpv"),
        Path("/usr/local/bin/mpv"),
    ]


def _winget_mpv_candidates() -> list[Path]:
    """Busca mpv.exe en paquetes WinGet portables (no el instalador GUI)."""
    packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if not packages.is_dir():
        return []
    found: list[Path] = []
    for pkg_dir in packages.iterdir():
        if "mpv" not in pkg_dir.name.lower():
            continue
        if _WINGET_GUI_PACKAGE.replace(".", "_") in pkg_dir.name.lower():
            continue
        found.extend(pkg_dir.rglob("mpv.exe"))
    return found


def find_mpv_binary() -> str | None:
    """
    Localiza el ejecutable mpv CLI.

    Orden en Windows: TERMINAL_RADIO_MPV -> Scoop -> WinGet portable -> PATH.
    Rechaza "MPV Player" (winget shinchiro.mpv) y valida con `mpv --version`.
    """
    override = os.environ.get(ENV_MPV_OVERRIDE)
    if override:
        path = Path(override)
        if path.is_file() and _verify_mpv_cli(path):
            return str(path.resolve())
        return None

    if sys.platform == "win32":
        for candidate in _windows_mpv_search_paths():
            if _is_rejected_windows_mpv(candidate):
                continue
            if _verify_mpv_cli(candidate):
                return str(candidate.resolve())
        return None

    found = shutil.which("mpv")
    if found and _verify_mpv_cli(Path(found)):
        return found

    if sys.platform.startswith("linux"):
        for candidate in _linux_known_paths():
            if _verify_mpv_cli(candidate):
                return str(candidate.resolve())

    return None


def mpv_available() -> bool:
    return find_mpv_binary() is not None


def python_version_ok() -> bool:
    return sys.version_info >= (3, 11)


def pip_available() -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def pip_install_steps() -> list[InstallStep]:
    """Pasos para instalar pip en la plataforma actual."""
    if is_termux():
        return [
            InstallStep(
                "Instalar pip con pkg (Termux)",
                ["pkg", "install", "-y", "python-pip"],
                verify_mpv=False,
            )
        ]

    if sys.platform == "darwin":
        return [
            InstallStep(
                "Instalar pip con ensurepip",
                [sys.executable, "-m", "ensurepip", "--upgrade", "--user"],
                verify_mpv=False,
            )
        ]

    if sys.platform.startswith("linux"):
        family = detect_linux_family()
        if family == LinuxFamily.DEBIAN:
            return [
                InstallStep(
                    "Instalar pip con apt",
                    ["sudo", "apt-get", "install", "-y", "python3-pip"],
                    verify_mpv=False,
                )
            ]
        if family == LinuxFamily.FEDORA:
            return [
                InstallStep(
                    "Instalar pip con dnf",
                    ["sudo", "dnf", "install", "-y", "python3-pip"],
                    verify_mpv=False,
                )
            ]
        if family == LinuxFamily.ARCH:
            return [
                InstallStep(
                    "Instalar pip con pacman",
                    ["sudo", "pacman", "-S", "--noconfirm", "python-pip"],
                    verify_mpv=False,
                )
            ]

    return [
        InstallStep(
            "Instalar pip con ensurepip",
            [sys.executable, "-m", "ensurepip", "--upgrade", "--user"],
            verify_mpv=False,
        )
    ]


def is_externally_managed() -> bool:
    """True si el SO bloquea pip global (PEP 668, Ubuntu 23.04+)."""
    marker = Path(sysconfig.get_path("stdlib")) / "EXTERNALLY-MANAGED"
    return marker.is_file()


def venv_python_path(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def is_repo_on_windows_mount(repo_root: Path) -> bool:
    """True si el repo esta en /mnt/... (WSL montando disco Windows)."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        resolved = repo_root.resolve().as_posix()
    except OSError:
        resolved = str(repo_root)
    return resolved.startswith("/mnt/")


def default_venv_dir(repo_root: Path) -> Path:
    """
    Ruta del venv para este repo.

    En WSL con repo en /mnt/c/... no se puede crear .venv ahi (symlinks/ensurepip).
    Se usa ~/.local/share/terminal-radio/venv en el filesystem nativo de Linux.
    """
    if is_repo_on_windows_mount(repo_root):
        return Path.home() / ".local" / "share" / "terminal-radio" / "venv"
    return repo_root / ".venv"


def venv_prereq_steps() -> list[InstallStep]:
    """Paquetes del sistema necesarios para crear un venv."""
    if is_termux():
        return []
    if sys.platform.startswith("linux"):
        family = detect_linux_family()
        if family == LinuxFamily.DEBIAN:
            return [
                InstallStep(
                    "Instalar venv y ensurepip (apt)",
                    [
                        "sudo",
                        "apt-get",
                        "install",
                        "-y",
                        "python3-venv",
                        "python3-full",
                    ],
                    verify_mpv=False,
                )
            ]
        if family == LinuxFamily.FEDORA:
            return [
                InstallStep(
                    "Instalar modulo venv (dnf)",
                    ["sudo", "dnf", "install", "-y", "python3-virtualenv"],
                    verify_mpv=False,
                )
            ]
    return []


def ensure_venv(venv_dir: Path, *, repo_root: Path | None = None) -> Path:
    """Crea o reutiliza un venv y devuelve la ruta al python del entorno."""
    python_path = venv_python_path(venv_dir)
    if python_path.is_file():
        return python_path

    if repo_root and is_repo_on_windows_mount(repo_root):
        print(
            "\n[aviso] El repo esta en /mnt/ (disco Windows via WSL). "
            "Los venv ahi suelen fallar."
        )
        print(f"  Usando venv en filesystem Linux: {venv_dir}")
        print("  Tip: clona el repo en ~/ para mejor rendimiento.")

    for step in venv_prereq_steps():
        run_install_step(step)

    venv_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n-> Crear entorno virtual en {venv_dir}")
    cmd = [sys.executable, "-m", "venv", str(venv_dir)]
    if is_repo_on_windows_mount(venv_dir):
        cmd.append("--copies")
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "No se pudo crear el venv. En Ubuntu/WSL: "
            "sudo apt install python3-venv python3-full"
        )
    if not python_path.is_file():
        raise RuntimeError(f"venv creado pero no se encontro {python_path}")
    print("  [ok] Entorno virtual listo")
    return python_path


def ensure_pip() -> bool:
    """Garantiza que pip este disponible para el Python actual."""
    if pip_available():
        return True

    for step in pip_install_steps():
        run_install_step(step)
        if pip_available():
            return True

    result = subprocess.run(
        [sys.executable, "-m", "ensurepip", "--upgrade", "--user"],
        check=False,
    )
    if result.returncode == 0 and pip_available():
        return True

    print("\npip no disponible. En Ubuntu/WSL prueba:")
    print("  sudo apt install python3-pip")
    return False


def refresh_windows_path() -> None:
    """Recarga PATH del usuario y del sistema (tras instalar con scoop/winget)."""
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:
        return

    parts: list[str] = []
    for hive, subkey in (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ):
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
                parts.append(value)
        except OSError:
            continue
    if parts:
        os.environ["PATH"] = ";".join(parts)


def detect_linux_family() -> LinuxFamily:
    if not sys.platform.startswith("linux"):
        return LinuxFamily.UNKNOWN

    try:
        os_release = Path("/etc/os-release").read_text(encoding="utf-8").lower()
    except OSError:
        return LinuxFamily.UNKNOWN

    if "id=ubuntu" in os_release or "id=debian" in os_release or "id=linuxmint" in os_release:
        return LinuxFamily.DEBIAN
    if "id=fedora" in os_release or "id=rhel" in os_release or "id=centos" in os_release:
        return LinuxFamily.FEDORA
    if "id=arch" in os_release or "id=manjaro" in os_release:
        return LinuxFamily.ARCH
    if "id=opensuse" in os_release or "id=sles" in os_release:
        return LinuxFamily.SUSE
    if "id=alpine" in os_release:
        return LinuxFamily.ALPINE
    return LinuxFamily.UNKNOWN


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _debian_mpv_install_steps() -> list[InstallStep]:
    """Ubuntu/Debian: apt primero; snap si apt no tiene el paquete (comun en WSL)."""
    steps: list[InstallStep] = [
        InstallStep(
            "Actualizar indice apt",
            ["sudo", "apt-get", "update"],
            verify_mpv=False,
        ),
        InstallStep(
            "Instalar mpv con apt",
            ["sudo", "apt-get", "install", "-y", "mpv"],
        ),
    ]
    if _command_exists("snap"):
        steps.append(
            InstallStep(
                "Instalar mpv con snap (fallback si apt no tiene el paquete)",
                ["sudo", "snap", "install", "mpv"],
            )
        )
    return steps


def mpv_install_steps() -> list[InstallStep]:
    """
    Pasos para instalar mpv CLI en la plataforma actual.

    En Windows prioriza gestores que dejan mpv.exe en PATH (Scoop, Chocolatey).
  No usa winget shinchiro.mpv (instala GUI sin CLI en PATH).
    """
    if is_termux():
        return [InstallStep("Instalar mpv con pkg (Termux)", ["pkg", "install", "-y", "mpv"])]

    if sys.platform == "darwin":
        if _command_exists("brew"):
            return [InstallStep("Instalar mpv con Homebrew", ["brew", "install", "mpv"])]
        return []

    if sys.platform == "win32":
        steps: list[InstallStep] = []
        if _command_exists("scoop"):
            steps.append(
                InstallStep(
                    "Anadir bucket extras de Scoop (si falta)",
                    ["scoop", "bucket", "add", "extras"],
                    verify_mpv=False,
                )
            )
            steps.append(InstallStep("Instalar mpv CLI con Scoop", ["scoop", "install", "mpv"]))
        if _command_exists("choco"):
            steps.append(
                InstallStep("Instalar mpv con Chocolatey", ["choco", "install", "mpv", "-y"])
            )
        if _command_exists("winget") and not _command_exists("scoop"):
            # Solo si no hay Scoop: build portable CI (zip), no el instalador GUI.
            steps.append(
                InstallStep(
                    "Instalar mpv portable con winget",
                    [
                        "winget",
                        "install",
                        "-e",
                        "--id",
                        "mpv-player.mpv-CI.MSVC",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                    ],
                )
            )
        return steps

    if sys.platform.startswith("linux"):
        family = detect_linux_family()
        if family == LinuxFamily.DEBIAN:
            return _debian_mpv_install_steps()
        if family == LinuxFamily.FEDORA:
            return [
                InstallStep(
                    "Instalar mpv con dnf",
                    ["sudo", "dnf", "install", "-y", "mpv"],
                )
            ]
        if family == LinuxFamily.ARCH:
            return [
                InstallStep(
                    "Instalar mpv con pacman",
                    ["sudo", "pacman", "-S", "--noconfirm", "mpv"],
                )
            ]
        if family == LinuxFamily.SUSE:
            return [
                InstallStep(
                    "Instalar mpv con zypper",
                    ["sudo", "zypper", "install", "-y", "mpv"],
                )
            ]
        if family == LinuxFamily.ALPINE:
            return [
                InstallStep(
                    "Instalar mpv con apk",
                    ["sudo", "apk", "add", "mpv"],
                )
            ]

    return []


def mpv_manual_instructions() -> str:
    """Instrucciones manuales cuando no hay gestor de paquetes detectado."""
    if is_termux():
        return "pkg install mpv"
    if sys.platform == "win32":
        return (
            "Instala el binario CLI de mpv (no el paquete GUI shinchiro.mpv de winget):\n"
            "  scoop bucket add extras\n"
            "  scoop install mpv\n"
            "  choco install mpv\n"
            "  https://mpv.io/installation/"
        )
    if sys.platform == "darwin":
        return "brew install mpv\n  https://mpv.io/installation/"
    family = detect_linux_family()
    hints = {
        LinuxFamily.DEBIAN: "sudo apt update && sudo apt install mpv\n  # si falla: sudo snap install mpv",
        LinuxFamily.FEDORA: "sudo dnf install mpv",
        LinuxFamily.ARCH: "sudo pacman -S mpv",
        LinuxFamily.SUSE: "sudo zypper install mpv",
        LinuxFamily.ALPINE: "sudo apk add mpv",
    }
    cmd = hints.get(family, "consulta el gestor de paquetes de tu distro")
    return f"{cmd}\n  https://mpv.io/installation/"


def run_install_step(step: InstallStep) -> bool:
    """Ejecuta un paso de instalación. Devuelve True si el proceso terminó con éxito."""
    print(f"\n-> {step.description}")
    print(f"  $ {' '.join(step.command)}")
    try:
        result = subprocess.run(step.command, shell=step.shell, check=False)
    except OSError as exc:
        print(f"  [error] No se pudo ejecutar: {exc}")
        return False
    if result.returncode == 0:
        print("  [ok] Comando completado")
        return True
    print(f"  [error] Codigo de salida: {result.returncode}")
    return False


def ensure_mpv() -> bool:
    """Intenta instalar mpv si no está disponible. Devuelve True si mpv es localizable."""
    if mpv_available():
        return True

    steps = mpv_install_steps()
    if not steps:
        print("\nNo se detecto un gestor de paquetes automatico para mpv.")
        print(mpv_manual_instructions())
        return False

    for step in steps:
        run_install_step(step)
        if sys.platform == "win32":
            refresh_windows_path()
        if step.verify_mpv and mpv_available():
            path = find_mpv_binary()
            print(f"\n[ok] mpv encontrado: {path}")
            return True

    if mpv_available():
        path = find_mpv_binary()
        print(f"\n[ok] mpv encontrado: {path}")
        return True

    print("\nmpv no localizable tras los intentos automaticos.")
    if sys.platform == "win32":
        print(
            "\n[aviso] Si instalaste 'MPV Player' con winget (shinchiro.mpv), "
            "es una app GUI que no deja mpv en PATH."
        )
        print("Usa Scoop en su lugar:")
        print("  scoop bucket add extras")
        print("  scoop install mpv")
    print("\nReinicia la terminal e intenta de nuevo, o define:")
    print(f"  set {ENV_MPV_OVERRIDE}=C:\\ruta\\a\\mpv.exe")
    print(mpv_manual_instructions())
    return False


# Wheels for packages that cannot compile on Termux (e.g. pydantic-core on Python 3.13).
TERMUX_PYPI_EXTRA_INDEXES: tuple[str, ...] = (
    "https://termux-user-repository.github.io/pypi/",
    "https://eutalix.github.io/android-pydantic-core/",
)


def termux_pip_extra_index_args() -> list[str]:
    """Extra pip indexes with pre-built Android wheels."""
    if not is_termux():
        return []
    args: list[str] = []
    for url in TERMUX_PYPI_EXTRA_INDEXES:
        args.extend(["--extra-index-url", url])
    return args


def termux_pip_install_args() -> list[str]:
    """
    Pip flags for Termux.

    --no-build-isolation is required: otherwise pip rebuilds pydantic-core in an
    isolated env even when it is already installed system-wide.
    """
    if not is_termux():
        return []
    return [
        "--no-build-isolation",
        "--prefer-binary",
        *termux_pip_extra_index_args(),
    ]


def _python_can_import(python: Path, module: str) -> bool:
    result = subprocess.run(
        [str(python), "-c", f"import {module}"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def ensure_termux_python_wheels(python: Path) -> bool:
    """
    Pre-install pydantic-core from community wheels.

    PyPI often has no wheel for aarch64-linux-android; pip then tries to
    compile via maturin/Rust and fails on Termux.
    """
    if not is_termux():
        return True

    if _python_can_import(python, "pydantic_core"):
        print("\n-> Termux: pydantic-core already installed")
        return True

    print("\n-> Termux: install pydantic-core (pre-built wheel)")
    for index in TERMUX_PYPI_EXTRA_INDEXES:
        cmd = [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "--prefer-binary",
            "--extra-index-url",
            index,
            "pydantic-core",
        ]
        print(f"  $ {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print("  [ok] pydantic-core")
            return True

    print_termux_pip_failure_hint()
    return False


TERMUX_APP_PIP_DEPS: tuple[str, ...] = (
    "httpx>=0.27.0",
    "pydantic-settings>=2.3.0",
    "textual>=0.80.0",
)


def ensure_termux_app_dependencies(python: Path) -> bool:
    """Install runtime deps on Termux before editable app install."""
    if not is_termux():
        return True
    if not ensure_termux_python_wheels(python):
        return False

    print("\n-> Termux: install Python dependencies")
    cmd = [
        str(python),
        "-m",
        "pip",
        "install",
        *termux_pip_install_args(),
        *TERMUX_APP_PIP_DEPS,
    ]
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("  [error] Failed to install Python dependencies on Termux")
        print_termux_pip_failure_hint()
        return False
    print("  [ok] dependencies")
    return True


def print_termux_pip_failure_hint() -> None:
    print(
        "\n  [error] Python dependency install failed on Termux.\n"
        "\n  If pydantic-core is missing, try one index:\n"
        "    pip install --no-build-isolation pydantic-core "
        "--extra-index-url https://termux-user-repository.github.io/pypi/\n"
        "    pip install --no-build-isolation pydantic-core "
        "--extra-index-url https://eutalix.github.io/android-pydantic-core/\n"
        "\n  Then: git pull && python scripts/install.py\n"
        "\n  Do not run `pip install --upgrade pip` on Termux "
        "(breaks the python-pip package).\n"
    )


def _ok(fail: bool) -> str:
    return "OK" if not fail else "FALTA"


def check_report() -> str:
    """Informe de dependencias para --check o install --check-only."""
    mpv_path = find_mpv_binary()
    lines = [
        f"Python {platform.python_version()}",
        f"  [{_ok(not python_version_ok())}] Se requiere Python 3.11+",
        "pip",
        f"  [{_ok(not pip_available())}] {'disponible' if pip_available() else 'no disponible'}",
        "mpv",
        f"  [{_ok(not mpv_available())}] {'encontrado' if mpv_available() else 'no encontrado'}",
    ]
    if mpv_path:
        lines.append(f"  ruta: {mpv_path}")
        lines.append("  tipo: CLI (mpv --version OK)")
    rejected = find_rejected_mpv_installs()
    if rejected:
        lines.append("  [aviso] Instalaciones GUI ignoradas (no compatibles):")
        for bad in rejected:
            lines.append(f"    - {bad}")
    if not mpv_available():
        lines.append("")
        lines.append("Como instalar mpv en esta plataforma:")
        for step in mpv_install_steps():
            lines.append(f"  {' '.join(step.command)}")
        if not mpv_install_steps():
            lines.append(mpv_manual_instructions())
    if is_termux():
        lines.append("")
        lines.append("Termux pip")
        lines.append("  pydantic-core needs a pre-built wheel (see TUR / Eutalix indexes)")
        for url in TERMUX_PYPI_EXTRA_INDEXES:
            lines.append(f"  --extra-index-url {url}")
    return "\n".join(lines)
