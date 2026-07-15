"""Dashboard zone -> clean PBIR page layout (row-compaction)."""

import xml.etree.ElementTree as ET

from tab2pbi.visual import layout
from tab2pbi.visual.ir import PageNode, Position, VisualNode

# Two sheets in one row (same y), one full-width row below, one off-canvas tooltip.
DASH_XML = """
<workbook>
  <dashboard name='D1'>
    <size maxwidth='1300' maxheight='900' minwidth='1300' minheight='900'/>
    <zone name='A' x='0'      y='0'     w='50000'  h='20000'/>
    <zone name='B' x='50000'  y='0'     w='50000'  h='20000'/>
    <zone name='C' x='0'      y='30000' w='100000' h='20000'/>
    <zone name='Tip' x='100000' y='-100' w='50' h='100'/>
  </dashboard>
</workbook>
"""


def _v(name):
    return VisualNode(worksheet=name, mark_type="Bar", visual_type="columnChart",
                      wells={"Y": []}, position=Position(0, 0, 0, 10, 10))


def _page():
    return PageNode(id="", name="D1", display_name="D1",
                    visuals=[_v("A"), _v("B"), _v("C"), _v("Tip")])


def _boxes(page):
    return {v.worksheet: v.position for v in page.visuals if v.emitted}


def _overlap(a, b):
    return not (a.x + a.width <= b.x or b.x + b.width <= a.x
                or a.y + a.height <= b.y or b.y + b.height <= a.y)


def test_no_overlaps_min_size_within_canvas():
    page = _page()
    layout.apply(ET.fromstring(DASH_XML), [page])
    boxes = list(_boxes(page).values())
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert not _overlap(a, b)
    assert all(p.width >= layout.MIN_W - 0.5 and p.height >= layout.MIN_H - 0.5 for p in boxes)
    assert all(0 <= p.x and 0 <= p.y and p.x + p.width <= page.width + 1
               and p.y + p.height <= page.height + 1 for p in boxes)


def test_same_row_side_by_side_and_next_row_below():
    page = _page()
    layout.apply(ET.fromstring(DASH_XML), [page])
    b = _boxes(page)
    assert b["A"].y == b["B"].y            # A and B share a row
    assert b["A"].x < b["B"].x             # left -> right order preserved
    assert b["C"].y > b["A"].y             # C is the row below


def test_offcanvas_tooltip_goes_to_overflow_not_content_flow():
    page = _page()
    layout.apply(ET.fromstring(DASH_XML), [page])
    b = _boxes(page)
    # Tip is parked off-canvas in Tableau -> placed in the overflow grid, below content.
    assert b["Tip"].y > b["C"].y


def test_page_height_is_compacted_not_fixed():
    page = _page()
    layout.apply(ET.fromstring(DASH_XML), [page])
    assert page.width == 1280
    # compacted content height, not a fixed 720 and not the raw 900-tall dashboard scale
    assert 200 < page.height < 1280
    assert page.layout == "dashboard-zones"


def test_deterministic():
    p1, p2 = _page(), _page()
    layout.apply(ET.fromstring(DASH_XML), [p1])
    layout.apply(ET.fromstring(DASH_XML), [p2])
    assert _boxes(p1) == _boxes(p2)


def test_no_geometry_uses_tidy_auto_grid():
    page = PageNode(id="", name="Other", display_name="Other", visuals=[_v("X"), _v("Y")])
    layout.apply(ET.fromstring("<workbook><dashboard name='Z'/></workbook>"), [page])
    assert page.layout == "auto-grid"
    boxes = list(_boxes(page).values())
    assert boxes[0].width == boxes[1].width      # uniform tiles
