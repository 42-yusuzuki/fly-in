"""Graph rendering onto a :class:`CellCanvas`.

Layer priority follows the visualizer design: connections, connection
metadata, zones, zone labels, then drones. Capacity marks are drawn
after labels but only onto cells no node or label uses, which yields the
same result as drawing them beneath those layers without leaving
partial marks.
"""

import math

from flyin.visualization.tui import palette
from flyin.visualization.tui.animation import (
    Anchor,
    DroneMotion,
    interpolate,
    turn_motions,
)
from flyin.visualization.tui.canvas import CellCanvas, raster_line
from flyin.visualization.tui.inspection import Selectable
from flyin.visualization.tui.model import VisualConnection, VisualMap, VisualZone
from flyin.visualization.tui.snapshot import (
    DroneActivity,
    DroneSnapshot,
    TurnSnapshot,
    group_by_link,
    link_key,
)
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


def badge_text(drones: tuple[DroneSnapshot, ...]) -> str:
    """Return the label for a group of drones drawn at one spot.

    A single drone shows its id (``D3``); a group shows its size
    (``D×4``) so the badge stays short on crowded zones.
    """
    if len(drones) == 1:
        return f"D{drones[0].drone_id}"
    return f"D×{len(drones)}"


def badge_style(drones: tuple[DroneSnapshot, ...]) -> str:
    """Return the badge style, letting the most eventful drone win."""
    activities = {drone.activity for drone in drones}
    if DroneActivity.ARRIVED in activities:
        return palette.DRONE_ARRIVED_STYLE
    if DroneActivity.MOVING in activities:
        return palette.DRONE_MOVING_STYLE
    if DroneActivity.IN_TRANSIT in activities:
        return palette.DRONE_TRANSIT_STYLE
    return palette.DRONE_WAITING_STYLE


class GraphRenderer:
    """Render a :class:`VisualMap`, optionally with drones at one turn."""

    def __init__(self, visual_map: VisualMap) -> None:
        """Create a renderer for one map.

        Args:
            visual_map: Map to draw. It is only read.
        """
        self._map = visual_map
        self._layout_cache: tuple[tuple[int, int], dict[str, Point]] | None = None

    def layout(self, width: int, height: int) -> dict[str, Point]:
        """Return the screen cell of every zone for a viewport size.

        The result is cached until the size changes, since it is needed
        on every animation frame.
        """
        if self._layout_cache is not None and self._layout_cache[0] == (
            width, height,
        ):
            return self._layout_cache[1]
        viewport = Viewport(self._map.bounds, width, height)
        ideal = {
            zone.name: viewport.to_cell(zone.world_x, zone.world_y)
            for zone in self._map.zones
        }
        cells = place_zones(ideal, width, height)
        self._layout_cache = ((width, height), cells)
        return cells

    def render(
        self,
        width: int,
        height: int,
        snapshot: TurnSnapshot | None = None,
        previous: TurnSnapshot | None = None,
        progress: float = 1.0,
        selected: Selectable | None = None,
    ) -> CellCanvas:
        """Draw the graph, plus the drones of ``snapshot`` if given.

        Args:
            width: Canvas width in columns.
            height: Canvas height in rows.
            snapshot: Turn whose drones, used connections, and zone
                occupancy are drawn; ``None`` draws the bare topology.
            previous: Turn before ``snapshot``, needed to animate the
                moves into it; ``None`` draws ``snapshot`` at rest.
            progress: How far the moves into ``snapshot`` have gone,
                from 0.0 (looks like ``previous``) to 1.0 (at rest).
            selected: Zone or connection to highlight, if any.
        """
        canvas = CellCanvas(width, height)
        if width == 0 or height == 0:
            return canvas

        cells = self.layout(width, height)
        usage = snapshot.link_usage() if snapshot else {}
        used = snapshot.used_links() if snapshot else frozenset()
        self._draw_connections(canvas, cells, usage, used, selected)
        self._draw_zones(canvas, cells, snapshot, selected)
        occupied = self._draw_labels(canvas, cells, selected)
        self._draw_connection_capacities(canvas, cells, occupied)
        if snapshot is not None:
            if previous is None or progress >= 1.0:
                motions: tuple[DroneMotion, ...] = ()
                stationary = tuple(d for d in snapshot.drones if d.on_map)
            else:
                motions, stationary = turn_motions(previous, snapshot)
            self._draw_drones(
                canvas, cells, stationary, motions, progress, occupied,
            )
        return canvas

    def _draw_connections(
        self,
        canvas: CellCanvas,
        cells: dict[str, Point],
        usage: dict[tuple[str, str], tuple[DroneSnapshot, ...]],
        used: frozenset[frozenset[str]],
        selected: Selectable | None,
    ) -> None:
        """Draw every connection, styled by how busy it is this turn.

        The selected connection is drawn last so it stays visible where
        lines cross.
        """
        ordered = sorted(
            self._map.connections, key=lambda conn: conn == selected,
        )
        for connection in ordered:
            x1, y1 = cells[connection.zone_a]
            x2, y2 = cells[connection.zone_b]
            canvas.line(
                x1, y1, x2, y2,
                self._connection_style(connection, usage, used, selected),
            )

    @staticmethod
    def _connection_style(
        connection: VisualConnection,
        usage: dict[tuple[str, str], tuple[DroneSnapshot, ...]],
        used: frozenset[frozenset[str]],
        selected: Selectable | None,
    ) -> str:
        """Pick selected, full, active (any drone moving on it), or idle."""
        if connection == selected:
            return palette.SELECTED_CONNECTION_STYLE
        key = link_key(connection.zone_a, connection.zone_b)
        if len(usage.get(key, ())) >= connection.max_capacity:
            return palette.FULL_CONNECTION_STYLE
        if frozenset(key) in used:
            return palette.ACTIVE_CONNECTION_STYLE
        return palette.CONNECTION_STYLE

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

    def _draw_zones(
        self,
        canvas: CellCanvas,
        cells: dict[str, Point],
        snapshot: TurnSnapshot | None,
        selected: Selectable | None,
    ) -> None:
        for zone in self._map.zones:
            x, y = cells[zone.name]
            style = palette.zone_style(zone)
            if zone == selected:
                style = palette.SELECTED_ZONE_STYLE
            elif (
                snapshot is not None
                and zone.max_drones is not None
                and len(snapshot.drones_at(zone.name)) >= zone.max_drones
            ):
                style += palette.FULL_ZONE_SUFFIX
            canvas.put(x, y, palette.zone_glyph(zone), style)

    def _draw_drones(
        self,
        canvas: CellCanvas,
        cells: dict[str, Point],
        stationary: tuple[DroneSnapshot, ...],
        motions: tuple[DroneMotion, ...],
        progress: float,
        decorated: set[Point],
    ) -> None:
        """Draw resting drones as grouped badges, then moving ones.

        Zone badges go just above their node (or below when that row is
        taken); badges of drones resting in transit sit on the middle of
        their connection. Moving drones glide between those same badge
        spots. A badge avoids the ``decorated`` cells (labels and
        capacity marks) when it can, and never covers a node or another
        badge when any candidate spot is free.
        """
        blocked: set[Point] = set(cells.values())

        for zone in self._map.zones:
            drones = tuple(d for d in stationary if d.zone == zone.name)
            if drones:
                x, y = cells[zone.name]
                self._draw_badge(
                    canvas, drones, (x, y - 1), [0, 2], blocked, decorated,
                )

        in_transit = tuple(d for d in stationary if d.zone is None)
        for (zone_a, zone_b), drones in group_by_link(in_transit).items():
            mid = self._anchor_cell(Anchor.midpoint(zone_a, zone_b), cells)
            self._draw_badge(canvas, drones, mid, [0, -1, 1], blocked, decorated)

        moving: dict[Point, list[DroneSnapshot]] = {}
        for motion in motions:
            screen_x, screen_y = interpolate(
                self._anchor_cell(motion.start, cells),
                self._anchor_cell(motion.end, cells),
                progress,
            )
            cell = (math.floor(screen_x + 0.5), math.floor(screen_y + 0.5))
            moving.setdefault(cell, []).append(motion.drone)
        for cell, group in moving.items():
            self._draw_badge(
                canvas, tuple(group), cell, [0, -1, 1], blocked, decorated,
            )

    @staticmethod
    def _anchor_cell(anchor: Anchor, cells: dict[str, Point]) -> Point:
        """Return the badge center for a zone or a connection midpoint.

        A zone's badge sits on the row above its node, so a drone at
        rest and a drone arriving there line up.
        """
        if anchor.other is None:
            x, y = cells[anchor.zone]
            return x, y - 1
        line = raster_line(*cells[anchor.zone], *cells[anchor.other])
        return line[len(line) // 2]

    def _draw_badge(
        self,
        canvas: CellCanvas,
        drones: tuple[DroneSnapshot, ...],
        center: Point,
        row_offsets: list[int],
        blocked: set[Point],
        decorated: set[Point],
    ) -> None:
        """Draw a group's badge centered on ``center``, trying each row."""
        text = badge_text(drones)
        x, y = center
        start_x = x - (len(text) - 1) // 2
        spots = [(start_x, y + offset) for offset in row_offsets]
        self._place_badge(
            canvas, text, badge_style(drones), spots, blocked, decorated,
        )

    @staticmethod
    def _place_badge(
        canvas: CellCanvas,
        text: str,
        style: str,
        spots: list[Point],
        blocked: set[Point],
        decorated: set[Point],
    ) -> None:
        """Draw ``text`` at the best spot, else clamped to the first.

        The first spot clear of both ``blocked`` and ``decorated`` wins,
        then the first clear of ``blocked`` only. Spots are shifted
        horizontally to fit the canvas. ``blocked`` is updated with the
        cells the badge now covers.
        """
        max_x = max(canvas.width - len(text), 0)
        candidates = [
            (min(max(x, 0), max_x), y) for x, y in spots
        ]
        chosen = None
        for avoid in (blocked | decorated, blocked):
            for x, y in candidates:
                badge_cells = {(x + i, y) for i in range(len(text))}
                if 0 <= y < canvas.height and not badge_cells & avoid:
                    chosen = (x, y)
                    break
            if chosen is not None:
                break
        if chosen is None:
            x, y = candidates[0]
            chosen = (x, min(max(y, 0), canvas.height - 1))
        x, y = chosen
        canvas.text(x, y, text, style)
        blocked.update((x + i, y) for i in range(len(text)))

    def _draw_labels(
        self,
        canvas: CellCanvas,
        cells: dict[str, Point],
        selected: Selectable | None = None,
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
            style = (
                palette.SELECTED_ZONE_STYLE if zone == selected
                else palette.label_style(zone)
            )
            canvas.text(start_x, y, text, style)
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
