"""The shared configuration of the pipeline: config/sector.yaml (kick-off layout)."""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_FILE = Path(__file__).resolve().parents[1] / "config" / "sector.yaml"


def load_config(path: Path = CONFIG_FILE) -> dict:
    """The configuration as a dictionary (read-only use: notebooks copy the values they need into named constants)."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
