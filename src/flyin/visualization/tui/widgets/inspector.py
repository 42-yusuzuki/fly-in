"""Panel describing the selected zone or connection at the current turn."""

from rich.text import Text
from textual.widgets import Static

from flyin.visualization.tui import palette
from flyin.visualization.tui.inspection import (
    LinkLoad,
    Selectable,
    ZoneReport,
    link_load,
    zone_report,
)
from flyin.visualization.tui.model import VisualMap, VisualZone, ZoneRole
from flyin.visualization.tui.snapshot import DroneActivity, TurnSnapshot
from flyin.visualization.tui.widgets.status_panel import add_heading, add_row

#: Drones listed for a connection before the rest become "+N more".
MAX_LISTED_DRONES = 6
_LINK_NAME_WIDTH = 16


def capacity_text(occupancy: int, limit: int | None) -> str:
    """Return ``occupancy / limit``, with ``∞`` for unlimited zones."""
    return f"{occupancy} / {'∞' if limit is None else limit}"


def build_inspector_text(
    visual_map: VisualMap, snapshot: TurnSnapshot, selected: Selectable,
) -> Text:
    """Return the inspector contents for ``selected`` at ``snapshot``."""
    text = Text(no_wrap=True, overflow="ellipsis")
    add_heading(text, f"SELECTED  (turn {snapshot.turn})")
    if isinstance(selected, VisualZone):
        _zone(text, zone_report(visual_map, selected, snapshot))
    else:
        _connection(text, link_load(selected, snapshot))
    return text


def _zone(text: Text, report: ZoneReport) -> None:
    zone = report.zone
    kind = zone.zone_type.value
    if zone.role is not ZoneRole.HUB:
        kind += f" · {zone.role.value}"
    add_row(text, "Zone", zone.name)
    add_row(text, "Type", kind)
    add_row(text, "Coordinate", f"({zone.world_x}, {zone.world_y})")
    _capacity(text, capacity_text(report.occupancy, zone.max_drones), report.full)
    drones = " ".join(f"D{drone.drone_id}" for drone in report.drones)
    add_row(text, "Drones", drones or "-")
    text.append("Connections\n", palette.MUTED_STYLE)
    for load in report.links:
        other = load.connection.other_end(zone.name)
        style = palette.FULL_STYLE if load.full else palette.LABEL_STYLE
        text.append(f"  {other:<{_LINK_NAME_WIDTH}}", style)
        text.append(
            f"{capacity_text(load.occupancy, load.connection.max_capacity)}\n",
            style,
        )


def _connection(text: Text, load: LinkLoad) -> None:
    connection = load.connection
    add_row(text, "Connection", connection.label)
    _capacity(
        text, capacity_text(load.occupancy, connection.max_capacity), load.full,
    )
    text.append("Drones\n", palette.MUTED_STYLE)
    listed = [(drone, False) for drone in load.drones]
    listed += [(drone, True) for drone in load.landing]
    if not listed:
        text.append("  -\n", palette.MUTED_STYLE)
    for drone, landing in listed[:MAX_LISTED_DRONES]:
        arrow = "⇢" if drone.activity is DroneActivity.IN_TRANSIT else "→"
        line = f"  D{drone.drone_id} {drone.source} {arrow} {drone.target}"
        if landing:
            text.append(f"{line} (landing)\n", palette.MUTED_STYLE)
        else:
            text.append(f"{line}\n", palette.LABEL_STYLE)
    hidden = len(listed) - MAX_LISTED_DRONES
    if hidden > 0:
        text.append(f"  +{hidden} more\n", palette.MUTED_STYLE)


def _capacity(text: Text, value: str, full: bool) -> None:
    if full:
        add_row(text, "Capacity", f"{value}  FULL", palette.FULL_STYLE)
    else:
        add_row(text, "Capacity", value)


class Inspector(Static):
    """Selection details; hidden while nothing is selected."""

    def __init__(self, visual_map: VisualMap, widget_id: str | None = None) -> None:
        """Create an empty, hidden inspector.

        Args:
            visual_map: Map the selections belong to.
            widget_id: Optional Textual widget id.
        """
        super().__init__("", id=widget_id)
        self._visual_map = visual_map
        self.display = False

    def show(self, snapshot: TurnSnapshot, selected: Selectable | None) -> None:
        """Describe ``selected`` at ``snapshot``, or hide when ``None``."""
        self.display = selected is not None
        if selected is not None:
            self.update(build_inspector_text(self._visual_map, snapshot, selected))
