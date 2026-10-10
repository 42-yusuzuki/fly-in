"""Glyphs and styles for the terminal visualizer.

Styles are Rich style strings. Zone *semantics* are always carried by
the glyph (start, end, and each zone type have distinct shapes), so a
map-provided color can be honored without making the zone type
ambiguous. Blocked zones ignore map colors and stay dimmed.
"""

from rich.color import Color, ColorParseError, ColorType

from flyin.domain.zone import ZoneType
from flyin.visualization.tui.model import VisualZone, ZoneRole

CONNECTION_STYLE = "#475569"
CAPACITY_STYLE = "#94a3b8"
LABEL_STYLE = "#cbd5e1"
MUTED_STYLE = "#64748b"
HEADING_STYLE = "bold #38bdf8"

ROLE_GLYPHS = {
    ZoneRole.START: "◉",
    ZoneRole.END: "◎",
}
TYPE_GLYPHS = {
    ZoneType.NORMAL: "●",
    ZoneType.PRIORITY: "◆",
    ZoneType.RESTRICTED: "▲",
    ZoneType.BLOCKED: "✖",
}
ROLE_STYLES = {
    ZoneRole.START: "bold #22c55e",
    ZoneRole.END: "bold #facc15",
}
TYPE_STYLES = {
    ZoneType.NORMAL: "#38bdf8",
    ZoneType.PRIORITY: "bold #2dd4bf",
    ZoneType.RESTRICTED: "#f43f5e",
    ZoneType.BLOCKED: "dim #6b7280",
}

# CSS color names seen in map files that Rich does not recognize.
_COLOR_ALIASES = {
    "orange": "#f97316",
    "crimson": "#dc143c",
    "gold": "#ffd700",
    "brown": "#a0522d",
    "darkred": "#b91c1c",
    "maroon": "#9f1239",
    "lime": "#84cc16",
    "gray": "#9ca3af",
    "grey": "#9ca3af",
}
# Explicit colors darker than this (0-255 luminance) vanish on the dark
# background. Standard ANSI colors are rendered by the terminal theme, so
# only ANSI black is rejected among them.
_MIN_LUMINANCE = 60.0
_ANSI_BLACK = 0


def zone_glyph(zone: VisualZone) -> str:
    """Return the single-character node glyph for a zone."""
    return ROLE_GLYPHS.get(zone.role, TYPE_GLYPHS[zone.zone_type])


def zone_style(zone: VisualZone) -> str:
    """Return the node style for a zone.

    Blocked zones are always dimmed. Otherwise a readable map color is
    used when available, falling back to the role or zone-type style.
    """
    if zone.zone_type is ZoneType.BLOCKED:
        return TYPE_STYLES[ZoneType.BLOCKED]

    fallback = ROLE_STYLES.get(zone.role, TYPE_STYLES[zone.zone_type])
    map_color = resolve_map_color(zone.color)
    if map_color is None:
        return fallback
    return f"bold {map_color}"


def label_style(zone: VisualZone) -> str:
    """Return the style for a zone's name label."""
    if zone.zone_type is ZoneType.BLOCKED:
        return TYPE_STYLES[ZoneType.BLOCKED]
    return ROLE_STYLES.get(zone.role, LABEL_STYLE)


def resolve_map_color(color: str | None) -> str | None:
    """Translate a map ``color=`` value into a usable Rich color.

    Returns ``None`` when the value is missing, not a recognizable
    color (e.g. ``rainbow``), or too dark to read on the background.
    """
    if not color:
        return None
    name = _COLOR_ALIASES.get(color.lower(), color.lower())
    try:
        parsed = Color.parse(name)
    except ColorParseError:
        return None
    if parsed.type is ColorType.STANDARD:
        return None if parsed.number == _ANSI_BLACK else name
    red, green, blue = parsed.get_truecolor()
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    if luminance < _MIN_LUMINANCE:
        return None
    return name
