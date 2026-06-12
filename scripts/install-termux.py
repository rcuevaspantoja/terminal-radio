#!/usr/bin/env python3
"""
Instalador Termux — mismo comando que install.py en desktop:

    python scripts/install-termux.py

También: sh scripts/install-termux.sh
"""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    impl = Path(__file__).resolve().parent / "install_termux.py"
    runpy.run_path(str(impl), run_name="__main__")
