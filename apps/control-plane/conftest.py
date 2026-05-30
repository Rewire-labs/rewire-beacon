"""Pytest bootstrap for the BEACON control-plane test suite.

Puts ``src/`` on ``sys.path`` so ``import beacon`` / ``import messaging_cp``
work when running ``pytest`` from the repo without an editable install.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
