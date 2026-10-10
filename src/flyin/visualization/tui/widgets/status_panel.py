"""Side panel summarizing map metadata and the zone legend."""

from rich.text import Text
from textual.widgets import Static

from flyin.domain.zone import ZoneType
from flyin.visualization.tui import palette
from flyin.visualization.tui.model import VisualMap, ZoneRole

_KEY_WIDTH = 13


def build_status_text(visual_map: VisualMap) -> Text:
    """Return the status panel contents for a map.

    Everything shown is derived from the presentation model only; no
    solver metric is computed here.
    """
    text = Text(no_wrap=True, overflow="ellipsis")
    bounds = visual_map.bounds
    start = _zone_name(visual_map, ZoneRole.START)
    end = _zone_name(visual_map, ZoneRole.END)

    _heading(text, "MAP")
    _row(text, "Name", visual_map.title)
    _row(text, "Drones", str(visual_map.drone_count))
    _row(text, "Zones", str(len(visual_map.zones)))
    _row(text, "Connections", str(len(visual_map.connections)))
    _row(text, "X range", f"{bounds.min_x} .. {bounds.max_x}")
    _row(text, "Y range", f"{bounds.min_y} .. {bounds.max_y}")
    text.append("\n")

    _heading(text, "LEGEND")
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
    _legend(text, "×", palette.CAPACITY_STYLE, "link capacity", "> 1")
    text.append("\n")

    _heading(text, "PLAYBACK")
    text.append("Static view (no simulation)\n", palette.MUTED_STYLE)
    return text


def _zone_name(visual_map: VisualMap, role: ZoneRole) -> str:
    """Return the name of the zone with the given role, or ``-``."""
    for zone in visual_map.zones:
        if zone.role is role:
            return zone.name
    return "-"


def _heading(text: Text, title: str) -> None:
    text.append(f"{title}\n", palette.HEADING_STYLE)


def _row(text: Text, key: str, value: str) -> None:
    text.append(f"{key:<{_KEY_WIDTH}}", palette.MUTED_STYLE)
    text.append(f"{value}\n", palette.LABEL_STYLE)


def _legend(text: Text, glyph: str, style: str, label: str, value: str) -> None:
    text.append(f"{glyph} ", style)
    text.append(f"{label:<{_KEY_WIDTH - 2}}", palette.MUTED_STYLE)
    text.append(f"{value}\n", palette.LABEL_STYLE)


class StatusPanel(Static):
    """Static panel showing map metadata and the glyph legend."""

    def __init__(self, visual_map: VisualMap, widget_id: str | None = None) -> None:
        """Create the panel.

        Args:
            visual_map: Map whose metadata is shown.
            widget_id: Optional Textual widget id.
        """
        super().__init__(build_status_text(visual_map), id=widget_id)
