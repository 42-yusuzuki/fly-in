"""Side panel summarizing the current turn, the map, and the legend."""

from rich.text import Text
from textual.widgets import Static

from flyin.domain.zone import ZoneType
from flyin.visualization.tui import palette
from flyin.visualization.tui.model import VisualMap, ZoneRole
from flyin.visualization.tui.snapshot import DroneActivity, TurnSnapshot

_KEY_WIDTH = 13
#: Moves listed before the rest are summarized as "+N more".
MAX_LISTED_MOVES = 8

_ACTIVITY_STYLES = {
    DroneActivity.WAITING: palette.DRONE_WAITING_STYLE,
    DroneActivity.MOVING: palette.DRONE_MOVING_STYLE,
    DroneActivity.IN_TRANSIT: palette.DRONE_TRANSIT_STYLE,
    DroneActivity.ARRIVED: palette.DRONE_ARRIVED_STYLE,
}


def build_status_text(
    visual_map: VisualMap,
    snapshot: TurnSnapshot,
    total_turns: int,
    playback: str | None = None,
) -> Text:
    """Return the status panel contents for one turn.

    Everything shown is derived from the presentation model and the
    precomputed snapshot; no solver metric is computed here.
    """
    text = Text(no_wrap=True, overflow="ellipsis")
    start = _zone_name(visual_map, ZoneRole.START)
    end = _zone_name(visual_map, ZoneRole.END)

    add_heading(text, "TURN")
    add_row(text, "Turn", f"{snapshot.turn} / {total_turns}")
    if playback is not None:
        add_row(text, "Playback", playback)
    _count(text, DroneActivity.WAITING, "Waiting",
           snapshot.count(DroneActivity.WAITING))
    _count(text, DroneActivity.MOVING, "Moving",
           snapshot.count(DroneActivity.MOVING))
    _count(text, DroneActivity.IN_TRANSIT, "In transit",
           snapshot.count(DroneActivity.IN_TRANSIT))
    _count(text, DroneActivity.ARRIVED, "Delivered",
           snapshot.delivered_count)
    text.append("\n")

    add_heading(text, "MAP")
    add_row(text, "Name", visual_map.title)
    add_row(text, "Drones", str(visual_map.drone_count))
    add_row(text, "Zones", str(len(visual_map.zones)))
    add_row(text, "Connections", str(len(visual_map.connections)))
    text.append("\n")

    add_heading(text, "LEGEND")
    _legend(text, palette.ROLE_GLYPHS[ZoneRole.START],
            palette.ROLE_STYLES[ZoneRole.START], "start", start)
    _legend(text, palette.ROLE_GLYPHS[ZoneRole.END],
            palette.ROLE_STYLES[ZoneRole.END], "end", end)
    counts = visual_map.zone_type_counts()
    for zone_type in ZoneType:
        _legend(
            text,
            palette.TYPE_GLYPHS[zone_type],
            palette.TYPE_STYLES[zone_type],
            zone_type.value,
            str(counts[zone_type]),
        )
    _legend(text, "×", palette.CAPACITY_STYLE, "link cap.", "> 1")
    text.append("\n")

    _moves(text, snapshot)
    return text


def _count(text: Text, activity: DroneActivity, label: str, value: int) -> None:
    text.append(" ", _ACTIVITY_STYLES[activity])
    text.append(f" {label:<{_KEY_WIDTH - 2}}", palette.MUTED_STYLE)
    text.append(f"{value}\n", palette.LABEL_STYLE)


def _moves(text: Text, snapshot: TurnSnapshot) -> None:
    """List the drones that used a connection during this turn."""
    movers = snapshot.movers()
    add_heading(text, "MOVES")
    if not movers:
        text.append("(none)\n", palette.MUTED_STYLE)
        return
    for drone in movers[:MAX_LISTED_MOVES]:
        arrow = "⇢" if drone.activity is DroneActivity.IN_TRANSIT else "→"
        text.append(f"D{drone.drone_id:<3}", _ACTIVITY_STYLES[drone.activity])
        text.append(f" {drone.source} {arrow} {drone.target}\n",
                    palette.LABEL_STYLE)
    hidden = len(movers) - MAX_LISTED_MOVES
    if hidden > 0:
        text.append(f"+{hidden} more\n", palette.MUTED_STYLE)


def _zone_name(visual_map: VisualMap, role: ZoneRole) -> str:
    """Return the name of the zone with the given role, or ``-``."""
    for zone in visual_map.zones:
        if zone.role is role:
            return zone.name
    return "-"


def add_heading(text: Text, title: str) -> None:
    """Append a section heading line."""
    text.append(f"{title}\n", palette.HEADING_STYLE)


def add_row(
    text: Text, key: str, value: str, value_style: str = palette.LABEL_STYLE,
) -> None:
    """Append an aligned ``key value`` line."""
    text.append(f"{key:<{_KEY_WIDTH}}", palette.MUTED_STYLE)
    text.append(f"{value}\n", value_style)


def _legend(text: Text, glyph: str, style: str, label: str, value: str) -> None:
    text.append(f"{glyph} ", style)
    text.append(f"{label:<{_KEY_WIDTH - 2}}", palette.MUTED_STYLE)
    text.append(f"{value}\n", palette.LABEL_STYLE)


class StatusPanel(Static):
    """Panel showing turn and playback state, map metadata, legend, moves."""

    def __init__(
        self,
        visual_map: VisualMap,
        snapshot: TurnSnapshot,
        total_turns: int,
        widget_id: str | None = None,
    ) -> None:
        """Create the panel.

        Args:
            visual_map: Map whose metadata is shown.
            snapshot: Turn shown initially.
            total_turns: Last turn of the simulation.
            widget_id: Optional Textual widget id.
        """
        super().__init__(
            build_status_text(visual_map, snapshot, total_turns), id=widget_id,
        )
        self._visual_map = visual_map
        self._total_turns = total_turns

    def show(self, snapshot: TurnSnapshot, playback: str | None = None) -> None:
        """Replace the contents with the given turn's status."""
        self.update(
            build_status_text(
                self._visual_map, snapshot, self._total_turns, playback,
            ),
        )
