#!/usr/bin/env sh
# Instalador Termux (Android). No uses: python scripts/install-termux.sh
# Usa en su lugar: python scripts/install-termux.py
set -e
cd "$(dirname "$0")/.."
if command -v python3 >/dev/null 2>&1; then
  exec python3 scripts/install-termux.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python scripts/install-termux.py "$@"
else
  echo "Error: Python 3.11+ no encontrado. Prueba: pkg install python" >&2
  exit 1
fi