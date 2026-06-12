"""Tests del monitor de rendimiento."""

from __future__ import annotations

from terminal_radio.debug.perf import PerfMonitor, configure_perf, perf


def test_perf_disabled_is_noop() -> None:
    monitor = PerfMonitor()
    monitor.configure(enabled=False)
    monitor.count("x")
    monitor.record_ms("y", 10.0)
    assert monitor.summary_lines()[0] == "Perf desactivado."


def test_perf_records_timings(tmp_path) -> None:
    monitor = PerfMonitor()
    monitor.configure(enabled=True, log_path=tmp_path / "perf.log")
    monitor.mark("a")
    monitor.record_since_mark("a", "latency")
    monitor.count("events", 3)
    lines = monitor.summary_lines()
    text = "\n".join(lines)
    assert "latency" in text
    assert "events: 3" in text
    written = monitor.write_report()
    assert written is not None
    assert written.is_file()


def test_configure_perf_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TERMINAL_RADIO_PERF", "1")
    configure_perf(log_path=tmp_path / "env-perf.log")
    assert perf.enabled is True
