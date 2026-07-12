"""Translate Tableau dashboard zones into PBIR page-canvas positions.

Tableau dashboard zones carry a ``name`` (the worksheet) and ``x/y/w/h`` in a
0–100000 normalized space relative to the dashboard size. We map those onto a
PBIR page canvas sized to the dashboard's aspect ratio. This is
**faithful-but-not-pixel-perfect**: relative placement/size is preserved, exact
pixels are not. Pages with no zone geometry keep the auto-grid layout.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..logging_config import get_logger
from .ir import PageNode, Position

log = get_logger(__name__)

_ZONE_SPACE = 100000.0


def _dashboard_geometry(root: ET.Element) -> dict[str, dict]:
    """dashboard name -> {w, h, zones: {worksheet: (x, y, w, h)}}."""
    out: dict[str, dict] = {}
    for dash in root.findall(".//dashboard"):
        name = dash.attrib.get("name")
        size = dash.find("./size")
        w = float(size.attrib.get("maxwidth", 1280)) if size is not None else 1280.0
        h = float(size.attrib.get("maxheight", 720)) if size is not None else 720.0
        zones: dict[str, tuple] = {}
        for z in dash.findall(".//zone"):
            zn = z.attrib.get("name")
            if zn and all(k in z.attrib for k in ("x", "y", "w", "h")):
                geom = (
                    float(z.attrib["x"]), float(z.attrib["y"]),
                    float(z.attrib["w"]), float(z.attrib["h"]),
                )
                # A worksheet can own several zones (sheet, legend, title);
                # keep the largest-area one as the visual's placement.
                prev = zones.get(zn)
                if prev is None or geom[2] * geom[3] > prev[2] * prev[3]:
                    zones[zn] = geom
        out[name] = {"w": w, "h": h, "zones": zones}
    return out


def apply(root: ET.Element, pages: list[PageNode], page_width: float = 1280) -> list[PageNode]:
    """Override auto-grid positions with dashboard-zone positions where available."""
    geom = _dashboard_geometry(root)
    for page in pages:
        d = geom.get(page.name)
        if not d or not d["zones"]:
            continue  # loose worksheets / no geometry -> keep auto-grid
        aspect = (d["h"] / d["w"]) if d["w"] else (720 / 1280)
        page.width = round(page_width, 2)
        page.height = round(page_width * aspect, 2)
        page.layout = "dashboard-zones"
        z = 0
        placed = 0
        for v in page.visuals:
            if not v.emitted:
                continue
            zone = d["zones"].get(v.worksheet)
            if zone is None:
                continue  # emitted visual with no zone -> keep its auto-grid slot
            zx, zy, zw, zh = zone
            # Clamp to a visible minimum and keep on-canvas: some designer zones
            # are tiny/hidden helper sheets; a 1px visual is useless. Position is
            # preserved approximately (faithful-not-pixel-perfect).
            min_w, min_h = 120.0, 90.0
            w_px = max(min_w, round(zw / _ZONE_SPACE * page.width, 2))
            h_px = max(min_h, round(zh / _ZONE_SPACE * page.height, 2))
            x_px = min(max(0.0, round(zx / _ZONE_SPACE * page.width, 2)), page.width - w_px)
            y_px = min(max(0.0, round(zy / _ZONE_SPACE * page.height, 2)), page.height - h_px)
            v.position = Position(x=x_px, y=y_px, z=z, width=w_px, height=h_px)
            z += 1
            placed += 1
        log.info("Dashboard '%s': placed %d visuals by zone geometry", page.name, placed)
    return pages
