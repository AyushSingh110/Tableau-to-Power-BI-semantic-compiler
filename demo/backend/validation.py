"""Validation for uploaded Tableau workbooks."""

from __future__ import annotations

import io
import zipfile


class DemoError(ValueError):
    """A user-facing error (returned as a clean JSON message, never a trace)."""


def validate_twbx(data: bytes) -> None:
    """Raise :class:`DemoError` unless ``data`` is a .twbx (zip with .twb + .hyper).

    A .twbx is a zip archive containing the Tableau workbook XML (.twb) and one
    or more Hyper extracts (.hyper). We check structure, not content depth.
    """
    if not data:
        raise DemoError("The uploaded file is empty.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
    except zipfile.BadZipFile as exc:
        raise DemoError("That doesn't look like a .twbx (not a valid zip archive).") from exc

    has_twb = any(n.lower().endswith(".twb") for n in names)
    has_hyper = any(n.lower().endswith(".hyper") for n in names)
    if not has_twb:
        raise DemoError("No .twb workbook found inside the archive.")
    if not has_hyper:
        raise DemoError(
            "No .hyper extract found inside the workbook. This demo needs a packaged "
            "extract (.twbx with embedded data), not a live-connection workbook."
        )
