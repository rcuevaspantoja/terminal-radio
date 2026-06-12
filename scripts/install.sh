#!/usr/bin/env sh
# Instalador Unix (Linux, macOS, Termux). Ejecuta el mismo install.py que Windows.
set -e
cd "$(dirname "$0")/.."
if command -v python3 >/dev/null 2>&1; then
  exec python3 scripts/install.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python scripts/install.py "$@"
else
  echo "Error: Python 3.11+ no encontrado." >&2
  exit 1
fi
