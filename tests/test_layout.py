"""Dashboard zone -> PBIR page-position translation."""

import xml.etree.ElementTree as ET

from tab2pbi.visual import layout
from tab2pbi.visual.ir import PageNode, Position, VisualNode

DASH_XML = """
<workbook>
  <dashboard name='D1'>
    <size maxwidth='1300' maxheight='650' minwidth='1300' minheight='650'/>
    <zones>
      <zone name='Sheet A' x='0' y='0' w='50000' h='100000'/>
      <zone name='Sheet A' x='10000' y='10000' w='2000' h='2000'/>
      <zone name='Sheet B' x='50000' y='0' w='50000' h='50000'/>
    </zones>
  </dashboard>
</workbook>
"""


def _page():
    a = VisualNode(worksheet="Sheet A", mark_type="Bar", visual_type="columnChart",
                   wells={"Y": []}, position=Position(0, 0, 0, 10, 10))
    b = VisualNode(worksheet="Sheet B", mark_type="Bar", visual_type="columnChart",
                   wells={"Y": []}, position=Position(0, 0, 0, 10, 10))
    return PageNode(id="", name="D1", display_name="D1", visuals=[a, b])


def test_page_sized_to_dashboard_aspect():
    root = ET.fromstring(DASH_XML)
    page = _page()
    layout.apply(root, [page])
    assert page.layout == "dashboard-zones"
    assert page.width == 1280
    assert round(page.height) == round(1280 * 650 / 1300)  # ~640


def test_largest_zone_wins_and_positions_scaled():
    root = ET.fromstring(DASH_XML)
    page = _page()
    layout.apply(root, [page])
    a = page.visuals[0].position
    # Sheet A's largest zone is 50000x100000 -> half width, full height (scaled).
    assert a.width == round(0.5 * page.width, 2)
    assert a.x == 0


def test_no_geometry_keeps_auto_grid():
    root = ET.fromstring("<workbook><dashboard name='Other'><zones/></dashboard></workbook>")
    page = _page()
    layout.apply(root, [page])
    assert page.layout == "auto-grid"  # unchanged
