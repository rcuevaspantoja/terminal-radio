#!/usr/bin/env sh
# Instalador Termux (Android). No usa pip install del proyecto.
set -e
cd "$(dirname "$0")/.."
if command -v python3 >/dev/null 2>&1; then
  exec python3 scripts/install_termux.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python scripts/install_termux.py "$@"
else
  echo "Error: Python 3.11+ no encontrado. Prueba: pkg install python" >&2
  exit 1
fi
