"""Wrap the TOM document as a Tabular Editor ``Model.json``."""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)


def run(tom: dict, data_dir: Path) -> dict:
    model_json = {"model": tom["model"]}
    with open(data_dir / "Model.json", "w", encoding="utf-8") as f:
        json.dump(model_json, f, indent=2)
    log.info("Tabular Editor Model.json written")
    return model_json
