"""Validate pipeline artifacts against the versioned IR JSON Schemas.

Schema violations raise ``SchemaValidationError`` so a malformed stage output
fails the pipeline loudly instead of propagating silently downstream.
"""

import json
from functools import cache
from pathlib import Path

import jsonschema

from ..logging_config import get_logger

log = get_logger(__name__)

SCHEMA_DIR = Path(__file__).parent / "schema"

SCHEMAS = {
    "semantic_model": "semantic_model.v1.schema.json",
    "final_model": "final_model.v1.schema.json",
}


class SchemaValidationError(ValueError):
    """Raised when an artifact does not conform to its IR schema."""


@cache
def _load_schema(name: str) -> dict:
    path = SCHEMA_DIR / SCHEMAS[name]
    return json.loads(path.read_text(encoding="utf-8"))


def validate(obj: dict, schema_name: str) -> None:
    """Validate ``obj`` against the named schema; raise on the first error."""
    schema = _load_schema(schema_name)
    try:
        jsonschema.validate(instance=obj, schema=schema)
    except jsonschema.ValidationError as exc:
        loc = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise SchemaValidationError(
            f"{schema_name} schema violation at {loc}: {exc.message}"
        ) from exc
    log.debug("%s conforms to %s", schema_name, SCHEMAS[schema_name])
