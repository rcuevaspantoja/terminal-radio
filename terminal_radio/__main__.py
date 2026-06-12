"""Entry point: terminal-radio / radio / python -m terminal_radio."""

from __future__ import annotations

import argparse
import atexit
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radio",
        description="Reproductor de radio por internet en terminal.",
    )
    from terminal_radio import __version__

    parser.add_argument(
        "--version",
        action="version",
        version=f"radio {__version__}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica dependencias del sistema (mpv, Python).",
    )
    parser.add_argument(
        "--perf",
        action="store_true",
        help="Activa diagnóstico de rendimiento (log en config dir).",
    )
    parser.add_argument(
        "--perf-log",
        type=str,
        default=None,
        metavar="PATH",
        help="Ruta del informe de rendimiento (implica --perf).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        from terminal_radio.platform.deps import check_report, mpv_available, python_version_ok

        print(check_report())
        return 0 if python_version_ok() and mpv_available() else 1

    from pathlib import Path

    from terminal_radio.app import TerminalRadioApp
    from terminal_radio.config import load_settings
    from terminal_radio.debug.perf import configure_perf, perf

    perf_enabled = args.perf or args.perf_log is not None
    log_path = Path(args.perf_log) if args.perf_log else None
    configure_perf(enabled=perf_enabled, log_path=log_path)

    def _write_perf_on_exit() -> None:
        if perf.enabled:
            report = perf.write_report()
            if report is not None:
                print(f"\n[terminal-radio perf] Informe: {report}", file=sys.stderr)

    atexit.register(_write_perf_on_exit)

    settings = load_settings()
    app = TerminalRadioApp(settings)
    try:
        app.run()
    finally:
        app.cleanup_resources()
        if perf.enabled:
            report = perf.write_report()
            if report is not None:
                print(f"\n[terminal-radio perf] Informe: {report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
