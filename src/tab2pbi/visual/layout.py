"""Translate Tableau dashboard zones into a clean PBIR page layout.

Tableau dashboard zones carry a ``name`` (the worksheet) and ``x/y/w/h`` in a
0–100000 space that is **absolute** within the dashboard. We do not reproduce
exact pixels (different layout engines); we produce a **clean, recognizably
faithful** page via *row-compaction*:

1. keep only on-canvas worksheet zones (off-canvas tooltip/hidden sheets are
   parked at x≈100000 in Tableau and are not dashboard content);
2. cluster the remaining visuals into rows by vertical proximity;
3. within each row, order left→right and size widths proportional to the zone
   widths; each row's height tracks its tallest zone;
4. stack rows top→bottom with uniform padding — deleting the empty bands left by
   skipped worksheets, so there are no giant gaps and (by construction) no
   overlaps.

Off-canvas / un-zoned emitted visuals are placed in a tidy grid below the
compacted rows so nothing is dropped or stacked. Pages with no dashboard
geometry use the same tidy grid. Deterministic: same input → same layout.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..logging_config import get_logger
from .ir import PageNode, Position, VisualNode

log = get_logger(__name__)

_ZONE_SPACE = 100000.0
MARGIN = 24.0
GAP = 16.0
MIN_W = 140.0
MIN_H = 90.0
DEFAULT_WIDTH = 1280.0


def _dashboard_geometry(root: ET.Element) -> dict[str, dict]:
    """dashboard name -> {w, h, zones: {worksheet: (x, y, w, h)}} (largest per name)."""
    out: dict[str, dict] = {}
    for dash in root.findall(".//dashboard"):
        name = dash.attrib.get("name")
        size = dash.find("./size")
        w = float(size.attrib.get("maxwidth", 1280)) if size is not None else 1280.0
        h = float(size.attrib.get("maxheight", 720)) if size is not None else 720.0
        zones: dict[str, tuple] = {}
        for z in dash.iter("zone"):
            zn = z.attrib.get("name")
            if zn and all(k in z.attrib for k in ("x", "y", "w", "h")):
                geom = tuple(float(z.attrib[k]) for k in ("x", "y", "w", "h"))
                prev = zones.get(zn)
                if prev is None or geom[2] * geom[3] > prev[2] * prev[3]:
                    zones[zn] = geom
        out[name] = {"w": w, "h": h, "zones": zones}
    return out


def _on_canvas(zone: tuple) -> bool:
    """True if the zone is real dashboard content (not a parked tooltip/hidden
    sheet). Tableau parks tooltip-only worksheets at x≈100000; require the
    majority of the zone to fall within the 0..100000 canvas."""
    x, y, w, h = zone
    if w <= 0 or h <= 0:
        return False
    if x >= _ZONE_SPACE or y >= _ZONE_SPACE or x + w <= 0 or y + h <= 0:
        return False
    vis_w = min(x + w, _ZONE_SPACE) - max(x, 0.0)
    vis_h = min(y + h, _ZONE_SPACE) - max(y, 0.0)
    if vis_w <= 0 or vis_h <= 0:
        return False
    return vis_w * vis_h >= 0.5 * w * h


def _cluster_rows(items: list[tuple[VisualNode, tuple]]) -> list[list[tuple[VisualNode, tuple]]]:
    """Group (visual, zone) by vertical proximity into left→right rows."""
    # Sort by zone top, then left, then worksheet name (deterministic).
    items = sorted(items, key=lambda it: (it[1][1], it[1][0], it[0].worksheet))
    rows: list[list[tuple[VisualNode, tuple]]] = []
    band: tuple[float, float] | None = None
    for v, z in items:
        top, bot = z[1], z[1] + z[3]
        if band is None:
            rows.append([(v, z)])
            band = (top, bot)
            continue
        # same row if vertical overlap exceeds 40% of the smaller height
        overlap = min(bot, band[1]) - max(top, band[0])
        smaller = min(bot - top, band[1] - band[0])
        if overlap > 0.4 * smaller:
            rows[-1].append((v, z))
            band = (min(band[0], top), max(band[1], bot))
        else:
            rows.append([(v, z)])
            band = (top, bot)
    # order visuals within each row left→right
    for row in rows:
        row.sort(key=lambda it: (it[1][0], it[0].worksheet))
    return rows


def _grid(visuals: list[VisualNode], start_y: float, width: float, z0: int, cols: int = 3) -> float:
    """Lay visuals in a tidy uniform grid starting at ``start_y``; return next y."""
    if not visuals:
        return start_y
    inner = width - 2 * MARGIN
    tile_w = (inner - (cols - 1) * GAP) / cols
    tile_h = max(MIN_H, tile_w * 0.6)
    y = start_y
    for i, v in enumerate(visuals):
        r, c = divmod(i, cols)
        v.position = Position(
            x=round(MARGIN + c * (tile_w + GAP), 2),
            y=round(start_y + r * (tile_h + GAP), 2),
            z=z0 + i, width=round(tile_w, 2), height=round(tile_h, 2),
        )
        y = start_y + (r + 1) * (tile_h + GAP)
    return y


def _place_rows(page: PageNode, rows, overflow: list[VisualNode], width: float) -> None:
    scale = width / _ZONE_SPACE
    inner = width - 2 * MARGIN
    z = 0
    y = MARGIN
    for row in rows:
        row_h = max(MIN_H, max(z[3] for _, z in row) * scale)
        total_zw = sum(z[2] for _, z in row) or 1.0
        k = len(row)
        avail = inner - (k - 1) * GAP
        widths = [max(MIN_W, avail * (z[2] / total_zw)) for _, z in row]
        if sum(widths) > avail:                       # renormalize to fit
            f = avail / sum(widths)
            widths = [w * f for w in widths]
        x = MARGIN
        for (v, _z), w_px in zip(row, widths, strict=False):
            v.position = Position(x=round(x, 2), y=round(y, 2), z=z,
                                  width=round(w_px, 2), height=round(row_h, 2))
            z += 1
            x += w_px + GAP
        y += row_h + GAP

    if overflow:
        y = _grid(overflow, y, width, z0=z)

    # Page dimensions are integers (matching Power BI's own page.json shape).
    page.width = int(round(width))
    page.height = int(round(y - GAP + MARGIN))   # trim trailing gap, add bottom margin


def apply(root: ET.Element, pages: list[PageNode], page_width: float = DEFAULT_WIDTH) -> list[PageNode]:
    """Assign clean positions: dashboard-zone row-compaction, or tidy auto-grid."""
    geom = _dashboard_geometry(root)
    for page in pages:
        emitted = [v for v in page.visuals if v.emitted]
        d = geom.get(page.name)
        if not d or not d["zones"]:
            page.layout = "auto-grid"
            bottom = _grid(emitted, MARGIN, page_width, z0=0)
            page.width = int(round(page_width))
            page.height = int(round(bottom - GAP + MARGIN)) if emitted else 720
            continue

        on, overflow = [], []
        for v in emitted:
            zone = d["zones"].get(v.worksheet)
            if zone and _on_canvas(zone):
                on.append((v, zone))
            else:
                overflow.append(v)   # off-canvas tooltip/hidden sheet -> overflow grid

        page.layout = "dashboard-zones"
        _place_rows(page, _cluster_rows(on), overflow, page_width)
        log.info(
            "Dashboard '%s': %d visuals in %d rows (+%d overflow) on a %gx%g canvas",
            page.name, len(on), len(_cluster_rows(on)), len(overflow), page.width, page.height,
        )
    return pages
