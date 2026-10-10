"""Tests for capacity reports and the inspector panel text."""

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.tui.inspection import link_load, selectables, zone_report
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots
from flyin.visualization.tui.widgets.inspector import (
    MAX_LISTED_DRONES,
    build_inspector_text,
    capacity_text,
)


def _visual_map() -> VisualMap:
    flyin_map = FlyInMap(
        drone_count=2,
        start="s",
        goal="g",
        zones={
            "s": Zone("s", 0, 0, ZoneType.NORMAL, 1),
            "A": Zone("A", 1, 0, ZoneType.NORMAL, 2),
            "R": Zone("R", 1, 1, ZoneType.RESTRICTED, 1),
            "g": Zone("g", 2, 0, ZoneType.NORMAL, 1),
        },
        connections=[
            Connection(1, "s", "A", 2),
            Connection(2, "s", "R", 1),
            Connection(3, "A", "g", 1),
            Connection(4, "R", "g", 1),
        ],
    )
    return VisualMap.from_flyin_map(flyin_map, "test")


def _snapshots() -> tuple[TurnSnapshot, ...]:
    """Drone 1 crosses s->A; drone 2 flies s->R over turns 1-2."""
    paths = [
        ["s", "A", "A", "g"],
        ["s", "s-R", "R", "g"],
    ]
    simulation = Simulation(paths=[
        DronePath(
            drone_id=index + 1,
            steps=[
                DroneStep(turn, location, on_connection="-" in location)
                for turn, location in enumerate(locations)
            ],
        )
        for index, locations in enumerate(paths)
    ])
    return build_snapshots(simulation, "g")


def test_selectables_list_zones_then_connections() -> None:
    visual = _visual_map()

    assert selectables(visual) == (*visual.zones, *visual.connections)


def test_zone_report_counts_occupancy_and_link_loads() -> None:
    visual = _visual_map()
    turn_1 = _snapshots()[1]

    report = zone_report(visual, visual.zone("s"), turn_1)

    assert [d.drone_id for d in report.drones] == []
    assert [load.connection.label for load in report.links] == [
        "s <-> A", "s <-> R",
    ]
    assert [load.occupancy for load in report.links] == [1, 1]
    assert [load.full for load in report.links] == [False, True]


def test_zone_full_only_for_limited_zones() -> None:
    visual = _visual_map()
    turn_0 = _snapshots()[0]

    start = zone_report(visual, visual.zone("s"), turn_0)
    assert start.occupancy == 2 and not start.full

    turn_1 = _snapshots()[1]
    hub = zone_report(visual, visual.zone("A"), turn_1)
    assert hub.occupancy == 1 and not hub.full


def test_landing_drone_is_listed_but_not_counted() -> None:
    visual = _visual_map()
    turn_2 = _snapshots()[2]
    s_to_r = visual.connections[1]

    load = link_load(s_to_r, turn_2)

    assert load.occupancy == 0
    assert [d.drone_id for d in load.landing] == [2]
    text = build_inspector_text(visual, turn_2, s_to_r).plain
    assert "0 / 1" in text
    assert "D2 s → R (landing)" in text


def test_inspector_text_for_zone() -> None:
    visual = _visual_map()
    text = build_inspector_text(visual, _snapshots()[0], visual.zone("s")).plain

    assert "SELECTED  (turn 0)" in text
    assert "Type         normal · start" in text
    assert "Capacity     2 / ∞" in text
    assert "Drones       D1 D2" in text


def test_inspector_text_flags_full_connection() -> None:
    visual = _visual_map()
    text = build_inspector_text(
        visual, _snapshots()[1], visual.connections[1],
    ).plain

    assert "Connection   s <-> R" in text
    assert "Capacity     1 / 1  FULL" in text
    assert "D2 s ⇢ R" in text


def test_inspector_truncates_long_drone_lists() -> None:
    visual = _visual_map()
    turn_1 = _snapshots()[1]
    crowded = TurnSnapshot(
        turn=1, drones=turn_1.drones[:1] * (MAX_LISTED_DRONES + 2),
    )

    text = build_inspector_text(visual, crowded, visual.connections[0]).plain

    assert "+2 more" in text


def test_capacity_text() -> None:
    assert capacity_text(1, 2) == "1 / 2"
    assert capacity_text(3, None) == "3 / ∞"
