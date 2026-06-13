"""Hooks para cerrar mpv cuando la consola/ventana se cierra (Windows)."""

from __future__ import annotations

import atexit
import sys
from collections.abc import Callable


def install_shutdown_hook(callback: Callable[[], None]) -> None:
    """Registra limpieza en atexit y al cerrar la ventana de consola (Windows)."""
    atexit.register(callback)

    if sys.platform != "win32":
        return

    import ctypes

    kernel32 = ctypes.windll.kernel32
    CTRL_CLOSE_EVENT = 2
    CTRL_LOGOFF_EVENT = 5
    CTRL_SHUTDOWN_EVENT = 6

    HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

    def _handler(ctrl_type: int) -> bool:
        if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
            callback()
            return True
        return False

    handler = HandlerRoutine(_handler)
    if not kernel32.SetConsoleCtrlHandler(handler, True):
        return

    # Evita que el handler sea recolectado por GC.
    install_shutdown_hook._handler = handler  # type: ignore[attr-defined]
