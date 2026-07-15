"""Make the repo root importable so `demo.backend.*` resolves under pytest."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
