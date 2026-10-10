"""Tests for the terminal visualizer's presentation model and palette."""

import pytest

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.visualization.tui import palette
from flyin.visualization.tui.model import VisualMap, VisualZone, ZoneRole


def _map() -> FlyInMap:
    return FlyInMap(
        drone_count=3,
        start="s",
        goal="g",
        zones={
            "s": Zone("s", -2, 0, ZoneType.NORMAL, 1, "green"),
            "r": Zone("r", 1, 4, ZoneType.RESTRICTED, 2),
            "g": Zone("g", 5, -1, ZoneType.NORMAL, 1),
        },
        connections=[
            Connection(1, "s", "r", 2),
            Connection(2, "r", "g", 1),
        ],
    )


def test_from_flyin_map_copies_topology_and_bounds() -> None:
    visual = VisualMap.from_flyin_map(_map(), "demo")

    assert visual.title == "demo"
    assert visual.drone_count == 3
    assert [zone.name for zone in visual.zones] == ["s", "r", "g"]
    assert [c.label for c in visual.connections] == ["s <-> r", "r <-> g"]
    assert visual.connections[0].max_capacity == 2
    bounds = visual.bounds
    assert (bounds.min_x, bounds.max_x) == (-2, 5)
    assert (bounds.min_y, bounds.max_y) == (-1, 4)


def test_start_and_end_have_unlimited_capacity() -> None:
    visual = VisualMap.from_flyin_map(_map(), "demo")

    assert visual.zone("s").role is ZoneRole.START
    assert visual.zone("s").max_drones is None
    assert visual.zone("g").role is ZoneRole.END
    assert visual.zone("g").max_drones is None
    assert visual.zone("r").role is ZoneRole.HUB
    assert visual.zone("r").max_drones == 2


def test_zone_type_counts() -> None:
    counts = VisualMap.from_flyin_map(_map(), "demo").zone_type_counts()

    assert counts[ZoneType.NORMAL] == 2
    assert counts[ZoneType.RESTRICTED] == 1
    assert counts[ZoneType.BLOCKED] == 0


def test_unknown_zone_name_raises() -> None:
    with pytest.raises(KeyError):
        VisualMap.from_flyin_map(_map(), "demo").zone("missing")


def test_map_without_zones_is_rejected() -> None:
    empty = FlyInMap(drone_count=1, start="s", goal="g", zones={}, connections=[])

    with pytest.raises(ValueError):
        VisualMap.from_flyin_map(empty, "empty")


def _zone(
    zone_type: ZoneType, role: ZoneRole = ZoneRole.HUB, color: str | None = None,
) -> VisualZone:
    return VisualZone("z", 0, 0, zone_type, role, 1, color)


def test_glyph_encodes_role_before_type() -> None:
    assert palette.zone_glyph(_zone(ZoneType.PRIORITY)) == "◆"
    assert palette.zone_glyph(_zone(ZoneType.RESTRICTED, ZoneRole.START)) == "◉"
    assert palette.zone_glyph(_zone(ZoneType.NORMAL, ZoneRole.END)) == "◎"


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (None, None),
        ("red", "red"),
        ("Orange", "#f97316"),
        ("rainbow", None),
        ("black", None),
        ("#101010", None),
        ("#ffd700", "#ffd700"),
    ],
)
def test_resolve_map_color(color: str | None, expected: str | None) -> None:
    assert palette.resolve_map_color(color) == expected


def test_zone_style_respects_map_color_but_keeps_blocked_dim() -> None:
    assert palette.zone_style(_zone(ZoneType.NORMAL, color="red")) == "bold red"
    assert palette.zone_style(_zone(ZoneType.NORMAL, color="rainbow")) == (
        palette.TYPE_STYLES[ZoneType.NORMAL]
    )
    assert palette.zone_style(_zone(ZoneType.BLOCKED, color="red")) == (
        palette.TYPE_STYLES[ZoneType.BLOCKED]
    )
