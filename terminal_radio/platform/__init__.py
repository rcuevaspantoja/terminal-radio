"""Detección de plataforma e integraciones opcionales del SO."""

from terminal_radio.platform.deps import check_report, ensure_mpv, mpv_available
from terminal_radio.platform.detect import get_config_dir

__all__ = [
    "check_report",
    "ensure_mpv",
    "get_config_dir",
    "mpv_available",
]
