"""Monitor de rendimiento opt-in para localizar cuellos de botella."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Iterator

from terminal_radio.platform.detect import get_config_dir


@dataclass
class _TimingStats:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def add(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        if duration_ms > self.max_ms:
            self.max_ms = duration_ms

    @property
    def avg_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_ms / self.count


class PerfMonitor:
    """Singleton ligero; sin overhead cuando está desactivado."""

    def __init__(self) -> None:
        self.enabled = False
        self._log_path: Path | None = None
        self._lock = threading.Lock()
        self._counts: dict[str, int] = defaultdict(int)
        self._timings: dict[str, _TimingStats] = defaultdict(_TimingStats)
        self._marks: dict[str, float] = {}
        self._meta: dict[str, str] = {}
        self._mpv_stderr_file: IO[str] | None = None
        self._started_at = time.monotonic()

    def configure(self, *, enabled: bool, log_path: Path | None = None) -> None:
        self.enabled = enabled
        if not enabled:
            return
        self._log_path = log_path or (get_config_dir() / "perf.log")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self.note("perf_log", str(self._log_path))

    def note(self, key: str, value: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._meta[key] = value

    def count(self, category: str, n: int = 1) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._counts[category] += n

    def record_ms(self, category: str, duration_ms: float) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._timings[category].add(duration_ms)

    def mark(self, label: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._marks[label] = time.perf_counter()

    def record_since_mark(self, label: str, category: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            started = self._marks.pop(label, None)
        if started is None:
            return
        self.record_ms(category, (time.perf_counter() - started) * 1000)

    @contextmanager
    def measure(self, category: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        started = time.perf_counter()
        try:
            yield
        finally:
            self.record_ms(category, (time.perf_counter() - started) * 1000)

    def mpv_stderr_target(self) -> int | IO[str]:
        """Destino de stderr de mpv cuando perf está activo."""
        if not self.enabled:
            return subprocess.DEVNULL
        if self._mpv_stderr_file is None:
            path = get_config_dir() / "mpv-stderr.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            self._mpv_stderr_file = path.open("w", encoding="utf-8")
            self.note("mpv_stderr_log", str(path))
        return self._mpv_stderr_file

    def close(self) -> None:
        if self._mpv_stderr_file is not None:
            try:
                self._mpv_stderr_file.close()
            except OSError:
                pass
            self._mpv_stderr_file = None

    def summary_lines(self) -> list[str]:
        if not self.enabled:
            return ["Perf desactivado."]
        elapsed = time.monotonic() - self._started_at
        lines = [
            "=== Terminal Radio — informe de rendimiento ===",
            f"Sesión: {elapsed:.1f}s",
        ]
        with self._lock:
            for key in sorted(self._meta):
                lines.append(f"  {key}: {self._meta[key]}")
            lines.append("")
            lines.append("Contadores:")
            for key in sorted(self._counts):
                lines.append(f"  {key}: {self._counts[key]}")
            lines.append("")
            lines.append("Tiempos (ms):")
            for key in sorted(self._timings):
                stats = self._timings[key]
                if stats.count == 0:
                    continue
                lines.append(
                    f"  {key}: n={stats.count} "
                    f"avg={stats.avg_ms:.2f} max={stats.max_ms:.2f}"
                )
        lines.append("")
        lines.append("Interpretación rápida:")
        lines.append(
            "  ui.arrow_to_highlight_ms alto → lag de Textual/lista (no mpv)"
        )
        lines.append(
            "  ipc.* alto en hilo principal → comandos mpv bloquean la TUI"
        )
        lines.append(
            "  player.notify alto → demasiadas actualizaciones de estado"
        )
        lines.append(
            "  ipc.property_change alto → metadata mpv muy frecuente"
        )
        lines.append(
            "  ui.player_bar_updated=0 → la barra no recibió estado"
        )
        lines.append(
            "  player_bar_region y>=altura terminal → barra fuera de pantalla"
        )
        return lines

    def write_report(self) -> Path | None:
        if not self.enabled or self._log_path is None:
            return None
        text = "\n".join(self.summary_lines()) + "\n"
        self._log_path.write_text(text, encoding="utf-8")
        return self._log_path

    def append_snapshot(self, label: str) -> None:
        if not self.enabled or self._log_path is None:
            return
        block = f"\n--- snapshot {label} ---\n" + "\n".join(self.summary_lines()) + "\n"
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(block)


perf = PerfMonitor()


def configure_perf(*, enabled: bool | None = None, log_path: Path | None = None) -> None:
    if enabled is None:
        enabled = os.environ.get("TERMINAL_RADIO_PERF", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
    perf.configure(enabled=enabled, log_path=log_path)
    if perf.enabled:
        perf.note("platform", sys.platform)
        perf.note("python", sys.version.split()[0])
        term = os.environ.get("WT_SESSION")
        perf.note(
            "terminal",
            "Windows Terminal" if term else os.environ.get("TERM", "unknown"),
        )
