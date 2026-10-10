"""Snapshot tests for the static terminal graph renderer."""

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.tui import palette
from flyin.visualization.tui.canvas import CellCanvas
from flyin.visualization.tui.inspection import Selectable
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.renderer import GraphRenderer, place_zones
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots


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


def _turn(turn: int, *paths: list[tuple[str, bool]]) -> TurnSnapshot:
    """Return the snapshot of ``turn`` for drones given as step lists."""
    simulation = Simulation(paths=[
        DronePath(
            drone_id=index + 1,
            steps=[
                DroneStep(step_turn, location, on_connection)
                for step_turn, (location, on_connection) in enumerate(steps)
            ],
        )
        for index, steps in enumerate(paths)
    ])
    return build_snapshots(simulation, "goal")[turn]


def _render_turn(
    snapshot: TurnSnapshot,
    width: int = 26,
    height: int = 3,
    capacity: int = 1,
    selected: Selectable | None = None,
) -> CellCanvas:
    visual = VisualMap.from_flyin_map(_linear_map(capacity=capacity), "test")
    return GraphRenderer(visual).render(
        width, height, snapshot, selected=selected,
    )


def test_waiting_drones_are_grouped_above_their_zone() -> None:
    at_start = [("start", False)]
    canvas = _render_turn(_turn(0, at_start, at_start, at_start))

    # The 3-cell badge is centered on the start node in column 2.
    assert canvas.plain_lines()[0].startswith(" D×3")
    assert canvas.get(2, 0).style == palette.DRONE_WAITING_STYLE


def test_single_drone_badge_shows_its_id_and_full_zone_is_emphasized() -> None:
    path = [("start", False), ("A", False)]
    canvas = _render_turn(_turn(1, path))
    lines = canvas.plain_lines()
    zone_x = lines[1].index("▲")

    assert lines[0][zone_x:zone_x + 2] == "D1"
    assert canvas.get(zone_x, 0).style == palette.DRONE_MOVING_STYLE
    assert canvas.get(zone_x, 1).style == (
        palette.TYPE_STYLES[ZoneType.RESTRICTED] + palette.FULL_ZONE_SUFFIX
    )
    start_x = lines[1].index("◉")
    # One drone on a capacity-1 link fills it.
    assert canvas.get(start_x + 1, 1).style == palette.FULL_CONNECTION_STYLE
    assert canvas.get(zone_x + 3, 1).style == palette.CONNECTION_STYLE


def test_used_link_below_capacity_is_active_not_full() -> None:
    path = [("start", False), ("A", False)]
    canvas = _render_turn(_turn(1, path), width=40, capacity=2)
    start_x = canvas.plain_lines()[1].index("◉")

    assert canvas.get(start_x + 1, 1).style == palette.ACTIVE_CONNECTION_STYLE


def test_selection_highlights_zone_and_label() -> None:
    visual = VisualMap.from_flyin_map(_linear_map(), "test")
    canvas = _render_turn(
        _turn(0, [("start", False)]), selected=visual.zone("A"),
    )
    line = canvas.plain_lines()[1]
    zone_x = line.index("▲")

    assert canvas.get(zone_x, 1).style == palette.SELECTED_ZONE_STYLE
    assert canvas.get(zone_x + 2, 1).style == palette.SELECTED_ZONE_STYLE
    assert canvas.get(line.index("◉"), 1).style != palette.SELECTED_ZONE_STYLE


def test_selected_connection_is_highlighted_over_usage() -> None:
    visual = VisualMap.from_flyin_map(_linear_map(), "test")
    path = [("start", False), ("A", False)]
    canvas = _render_turn(_turn(1, path), selected=visual.connections[0])
    start_x = canvas.plain_lines()[1].index("◉")

    assert canvas.get(start_x + 1, 1).style == palette.SELECTED_CONNECTION_STYLE


def test_transit_badge_sits_on_the_connection() -> None:
    path = [("start", False), ("start-A", True), ("A", False)]
    canvas = _render_turn(_turn(1, path), width=40)
    lines = canvas.plain_lines()

    assert "D1" in lines[1]
    assert lines[1].index("◉") < lines[1].index("D1") < lines[1].index("▲")
    assert lines[0].strip() == "" and lines[2].strip() == ""


def test_badge_moves_below_rather_than_covering_a_label() -> None:
    flyin_map = FlyInMap(
        drone_count=1,
        start="start",
        goal="goal",
        zones={
            "start": Zone("start", 1, 0, ZoneType.NORMAL, 1),
            "abc": Zone("abc", 0, 1, ZoneType.NORMAL, 1),
            "goal": Zone("goal", 10, 0, ZoneType.NORMAL, 1),
        },
        connections=[
            Connection(1, "start", "goal", 1),
            Connection(2, "abc", "start", 1),
        ],
    )
    visual = VisualMap.from_flyin_map(flyin_map, "test")
    snapshot = _turn(0, [("start", False)])

    plain = GraphRenderer(visual).render(22, 4, snapshot).plain_lines()

    # The row above start holds the "abc" label, so the badge goes below.
    assert "abc" in plain[1]
    assert "D1" not in plain[1]
    assert plain[3].index("D1") == plain[2].index("◉")


def test_moving_drone_is_drawn_between_zones_mid_turn() -> None:
    path = [("start", False), ("A", False)]
    visual = VisualMap.from_flyin_map(_linear_map(), "test")
    renderer = GraphRenderer(visual)
    before, after = _turn(0, path), _turn(1, path)

    def badge_x(progress: float) -> int:
        lines = renderer.render(40, 4, after, before, progress).plain_lines()
        row = next(line for line in lines if "D1" in line)
        return row.index("D1")

    start, middle, end = badge_x(0.0), badge_x(0.5), badge_x(1.0)

    assert start < middle < end
    lines = renderer.render(40, 4, after, before, 1.0).plain_lines()
    assert lines == renderer.render(40, 4, after).plain_lines()


def test_hit_test_finds_nodes_labels_and_connections() -> None:
    visual = VisualMap.from_flyin_map(_linear_map(), "test")
    renderer = GraphRenderer(visual)
    # "  ◉─start────▲─A──goal─◎  "
    line = renderer.render(26, 3).plain_lines()[1]

    assert renderer.hit_test(26, 3, line.index("◉"), 1) == visual.zone("start")
    assert renderer.hit_test(26, 3, line.index("goal"), 1) == visual.zone("goal")
    assert renderer.hit_test(26, 3, line.index("────"), 1) == visual.connections[0]
    # One row above a node still selects it; far away selects nothing.
    assert renderer.hit_test(26, 3, line.index("▲"), 0) == visual.zone("A")
    assert renderer.hit_test(26, 3, 0, 0) is None
