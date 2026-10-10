"""Static graph rendering onto a :class:`CellCanvas`.

Layer priority follows the visualizer design: connections, connection
metadata, zones, then zone labels. Capacity marks are drawn last but
only onto cells no node or label uses, which yields the same result as
drawing them beneath those layers without leaving partial marks.
"""

from flyin.visualization.tui import palette
from flyin.visualization.tui.canvas import CellCanvas
from flyin.visualization.tui.model import VisualMap, VisualZone
from flyin.visualization.tui.viewport import Viewport

#: How far (in cells) a zone may be nudged when its ideal cell is taken.
PLACEMENT_RADIUS = 2
_ELLIPSIS = "…"
_MIN_LABEL_CHARS = 2

Point = tuple[int, int]


def place_zones(
    ideal: dict[str, Point],
    width: int,
    height: int,
    radius: int = PLACEMENT_RADIUS,
) -> dict[str, Point]:
    """Assign each zone a distinct cell as close as possible to its ideal.

    Zones are processed in the dict's order. A zone whose ideal cell is
    already taken moves to the nearest free cell within ``radius``
    (Chebyshev distance); if none is free it keeps its ideal cell and
    overlaps. Only screen positions change, never map coordinates.

    Args:
        ideal: Ideal cell for each zone name.
        width: Canvas width in columns.
        height: Canvas height in rows.
        radius: Maximum nudge distance.
    """
    taken: set[Point] = set()
    placed: dict[str, Point] = {}
    for name, cell in ideal.items():
        chosen = _nearest_free(cell, taken, width, height, radius)
        placed[name] = chosen
        taken.add(chosen)
    return placed


def _nearest_free(
    cell: Point,
    taken: set[Point],
    width: int,
    height: int,
    radius: int,
) -> Point:
    """Return the closest free in-bounds cell around ``cell``."""
    if cell not in taken:
        return cell
    x, y = cell
    candidates = [
        (x + dx, y + dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if (dx, dy) != (0, 0)
    ]
    # Prefer horizontal nudges: terminal cells are taller than wide.
    candidates.sort(key=lambda p: (abs(p[1] - y) * 2 + abs(p[0] - x)))
    for cand_x, cand_y in candidates:
        if (
            0 <= cand_x < width
            and 0 <= cand_y < height
            and (cand_x, cand_y) not in taken
        ):
            return cand_x, cand_y
    return cell


class GraphRenderer:
    """Render the static topology of a :class:`VisualMap`."""

    def __init__(self, visual_map: VisualMap) -> None:
        """Create a renderer for one map.

        Args:
            visual_map: Map to draw. It is only read.
        """
        self._map = visual_map

    def layout(self, width: int, height: int) -> dict[str, Point]:
        """Return the screen cell of every zone for a viewport size."""
        viewport = Viewport(self._map.bounds, width, height)
        ideal = {
            zone.name: viewport.to_cell(zone.world_x, zone.world_y)
            for zone in self._map.zones
        }
        return place_zones(ideal, width, height)

    def render(self, width: int, height: int) -> CellCanvas:
        """Draw connections, capacities, zones, and labels to a new canvas."""
        canvas = CellCanvas(width, height)
        if width == 0 or height == 0:
            return canvas

        cells = self.layout(width, height)
        self._draw_connections(canvas, cells)
        self._draw_zones(canvas, cells)
        occupied = self._draw_labels(canvas, cells)
        self._draw_connection_capacities(canvas, cells, occupied)
        return canvas

    def _draw_connections(
        self, canvas: CellCanvas, cells: dict[str, Point],
    ) -> None:
        for connection in self._map.connections:
            x1, y1 = cells[connection.zone_a]
            x2, y2 = cells[connection.zone_b]
            canvas.line(x1, y1, x2, y2, palette.CONNECTION_STYLE)

    def _draw_connection_capacities(
        self,
        canvas: CellCanvas,
        cells: dict[str, Point],
        occupied: set[Point],
    ) -> None:
        """Mark links whose capacity is above the default of 1.

        A mark is skipped entirely if any of its cells is ``occupied``
        (by a node or label) or lies off the canvas.
        """
        for connection in self._map.connections:
            if connection.max_capacity <= 1:
                continue
            x1, y1 = cells[connection.zone_a]
            x2, y2 = cells[connection.zone_b]
            mark = f"×{connection.max_capacity}"
            mid_x = (x1 + x2) // 2 - len(mark) // 2
            mid_y = (y1 + y2) // 2
            mark_cells = {(mid_x + i, mid_y) for i in range(len(mark))}
            if mark_cells & occupied or not all(
                canvas.in_bounds(x, y) for x, y in mark_cells
            ):
                continue
            canvas.text(mid_x, mid_y, mark, palette.CAPACITY_STYLE)
            occupied |= mark_cells

    def _draw_zones(self, canvas: CellCanvas, cells: dict[str, Point]) -> None:
        for zone in self._map.zones:
            x, y = cells[zone.name]
            canvas.put(x, y, palette.zone_glyph(zone), palette.zone_style(zone))

    def _draw_labels(
        self, canvas: CellCanvas, cells: dict[str, Point],
    ) -> set[Point]:
        """Place labels beside nodes, truncating rather than overlapping.

        A label never covers a node or a previously placed label. It goes
        to the right of its node when it fits, otherwise to whichever
        side has more room, truncated with an ellipsis; labels with too
        little room are hidden.

        Returns:
            Every cell now used by a node or a label.
        """
        blocked: set[Point] = set(cells.values())
        for zone in self._map.zones:
            x, y = cells[zone.name]
            text, start_x = self._fit_label(zone, x, y, canvas.width, blocked)
            if not text:
                continue
            canvas.text(start_x, y, text, palette.label_style(zone))
            blocked.update((start_x + i, y) for i in range(len(text)))
        return blocked

    def _fit_label(
        self,
        zone: VisualZone,
        x: int,
        y: int,
        width: int,
        blocked: set[Point],
    ) -> tuple[str, int]:
        """Return ``(text, start_x)`` for a zone label, or ``("", 0)``."""
        name = zone.name
        right_room = _free_run(x + 2, y, 1, width, blocked)
        left_room = _free_run(x - 2, y, -1, width, blocked)

        if right_room >= len(name) or right_room >= left_room:
            text = _truncate(name, right_room)
            return text, x + 2
        text = _truncate(name, left_room)
        return text, x - 1 - len(text)


def _free_run(
    x: int, y: int, direction: int, width: int, blocked: set[Point],
) -> int:
    """Count consecutive free cells from ``x`` in ``direction``.

    One extra cell next to the node is kept as a gap, so the run starts
    two cells away from the node and stops one cell before an obstacle.
    """
    run = 0
    while 0 <= x < width and (x, y) not in blocked:
        if (x + direction, y) in blocked:
            break
        run += 1
        x += direction
    return run


def _truncate(name: str, room: int) -> str:
    """Fit ``name`` into ``room`` cells, or return ``""`` if too cramped."""
    if room >= len(name):
        return name
    if room < _MIN_LABEL_CHARS:
        return ""
    return name[: room - 1] + _ELLIPSIS
