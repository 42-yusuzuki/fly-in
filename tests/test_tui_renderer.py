"""Snapshot tests for the static terminal graph renderer."""

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.renderer import GraphRenderer, place_zones


def _linear_map(name_a: str = "A", capacity: int = 1) -> FlyInMap:
    return FlyInMap(
        drone_count=1,
        start="start",
        goal="goal",
        zones={
            "start": Zone("start", 0, 0, ZoneType.NORMAL, 1),
            name_a: Zone(name_a, 5, 0, ZoneType.RESTRICTED, 1),
            "goal": Zone("goal", 10, 0, ZoneType.NORMAL, 1),
        },
        connections=[
            Connection(1, "start", name_a, capacity),
            Connection(2, name_a, "goal", 1),
        ],
    )


def _render(flyin_map: FlyInMap, width: int, height: int) -> list[str]:
    visual = VisualMap.from_flyin_map(flyin_map, "test")
    return GraphRenderer(visual).render(width, height).plain_lines()


def test_linear_map_snapshot() -> None:
    assert _render(_linear_map(), 26, 3) == [
        "                          ",
        "  ◉─start────▲─A──goal─◎  ",
        "                          ",
    ]


def test_link_capacity_mark_is_drawn_on_free_edge_cells() -> None:
    lines = _render(_linear_map(capacity=3), 40, 3)

    assert "×3" in lines[1]
    assert lines[1].index("start") < lines[1].index("×3") < lines[1].index("▲")


def test_long_labels_are_truncated_not_overlapping() -> None:
    lines = _render(_linear_map(name_a="very_long_zone_name"), 26, 3)

    assert lines[1].count("◉") == 1
    assert lines[1].count("▲") == 1
    assert lines[1].count("◎") == 1
    assert "…" in lines[1]


def test_vertical_layout_uses_y_axis_upward() -> None:
    flyin_map = FlyInMap(
        drone_count=1,
        start="s",
        goal="g",
        zones={
            "s": Zone("s", 0, 0, ZoneType.NORMAL, 1),
            "g": Zone("g", 0, 4, ZoneType.NORMAL, 1),
        },
        connections=[Connection(1, "s", "g", 1)],
    )

    lines = _render(flyin_map, 7, 7)

    assert [line[3] for line in lines] == [" ", "◎", "│", "│", "│", "◉", " "]


def test_render_handles_zero_size() -> None:
    assert _render(_linear_map(), 0, 0) == []


def test_place_zones_nudges_colliding_zones() -> None:
    placed = place_zones({"a": (5, 5), "b": (5, 5), "c": (5, 5)}, 20, 20)

    assert placed["a"] == (5, 5)
    assert len(set(placed.values())) == 3
    for x, y in placed.values():
        assert abs(x - 5) <= 2 and abs(y - 5) <= 2


def test_place_zones_prefers_horizontal_nudge() -> None:
    placed = place_zones({"a": (5, 5), "b": (5, 5)}, 20, 20)

    assert placed["b"][1] == 5


def test_place_zones_keeps_ideal_cell_when_no_room() -> None:
    placed = place_zones({"a": (0, 0), "b": (0, 0)}, 1, 1)

    assert placed == {"a": (0, 0), "b": (0, 0)}
