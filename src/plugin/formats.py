"""The bundled formats, as src/plugin/data/<format>.json holds them."""

from __future__ import annotations

import json
from pathlib import Path

from contract import Format

DATA = Path(__file__).parent / "data"


def load_format(format: Format) -> dict:
    """``{"format", "description", "target", "positives", "negatives", "max_length", "heldout": [[text, member]]}``."""
    return json.loads((DATA / f"{format.value}.json").read_text())
