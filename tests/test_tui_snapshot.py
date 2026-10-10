"""Tests for per-turn drone snapshots used by the terminal visualizer."""

import pytest

from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.tui.snapshot import (
    DroneActivity,
    DroneSnapshot,
    TurnSnapshot,
    build_snapshots,
)


def _path(drone_id: int, *locations: str, transit: int | None = None) -> DronePath:
    """Build a path from one location per turn; ``transit`` marks a turn."""
    return DronePath(
        drone_id=drone_id,
        steps=[
            DroneStep(turn=turn, location=location, on_connection=turn == transit)
            for turn, location in enumerate(locations)
        ],
    )


def _snapshots(*paths: list[str]) -> tuple[TurnSnapshot, ...]:
    """Build snapshots; locations containing ``-`` are connections."""
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


def _simulation() -> Simulation:
    return Simulation(paths=[
        # Waits one turn, moves to A, then reaches the goal.
        _path(1, "s", "s", "A", "g"),
        # Flies to restricted R over two turns, then reaches the goal.
        _path(2, "s", "s-R", "R", "g", transit=1),
    ])


def test_one_snapshot_per_turn_including_turn_zero() -> None:
    snapshots = build_snapshots(_simulation(), "g")

    assert [snapshot.turn for snapshot in snapshots] == [0, 1, 2, 3]


def test_drone_activities_follow_the_paths() -> None:
    snapshots = build_snapshots(_simulation(), "g")

    def drone(turn: int, drone_id: int) -> DroneSnapshot:
        return snapshots[turn].drones[drone_id - 1]

    assert drone(0, 1) == DroneSnapshot(1, DroneActivity.WAITING, "s")
    assert drone(1, 1) == DroneSnapshot(1, DroneActivity.WAITING, "s")
    assert drone(2, 1) == DroneSnapshot(1, DroneActivity.MOVING, "A", "s", "A")
    assert drone(3, 1) == DroneSnapshot(1, DroneActivity.ARRIVED, "g", "A", "g")

    assert drone(1, 2) == DroneSnapshot(
        2, DroneActivity.IN_TRANSIT, None, "s", "R",
    )
    # Landing reports the zone the transit started from.
    assert drone(2, 2) == DroneSnapshot(
        2, DroneActivity.MOVING, "R", "s", "R", landing=True,
    )


def test_drones_delivered_earlier_leave_the_map() -> None:
    simulation = Simulation(paths=[
        _path(1, "s", "g"),
        _path(2, "s", "s", "s", "g"),
    ])

    snapshot = build_snapshots(simulation, "g")[2]

    assert snapshot.drones[0].activity is DroneActivity.DELIVERED
    assert not snapshot.drones[0].on_map
    assert snapshot.drones_at("g") == ()
    assert snapshot.delivered_count == 1


def test_counts_partition_the_fleet() -> None:
    for snapshot in build_snapshots(_simulation(), "g"):
        assert snapshot.count(*DroneActivity) == 2


def test_used_links_and_transit_groups() -> None:
    simulation = Simulation(paths=[
        _path(1, "A", "A-R", "R", transit=1),
        _path(2, "R", "A-R", "A", transit=1),
        _path(3, "A", "B", "B"),
    ])

    turn_1 = build_snapshots(simulation, "g")[1]

    assert turn_1.used_links() == {frozenset({"A", "R"}), frozenset({"A", "B"})}
    groups = turn_1.transit_groups()
    assert list(groups) == [("A", "R")]
    assert [drone.drone_id for drone in groups[("A", "R")]] == [1, 2]
    assert [drone.drone_id for drone in turn_1.movers()] == [1, 2, 3]


def test_path_ending_on_a_connection_is_rejected() -> None:
    simulation = Simulation(paths=[_path(1, "s", "s-R", transit=1)])

    with pytest.raises(ValueError):
        build_snapshots(simulation, "g")


def test_link_usage_counts_transit_once() -> None:
    snapshots = _snapshots(["s", "s-R", "R"], ["s", "s", "s-R", "R"])

    turn_2 = snapshots[2]

    # Drone 1 lands (counted on turn 1); drone 2 takes off.
    assert {k: [d.drone_id for d in v] for k, v in turn_2.link_usage().items()} == {
        ("R", "s"): [2],
    }
    assert [d.drone_id for d in turn_2.landings()[("R", "s")]] == [1]
    assert turn_2.used_links() == {frozenset({"s", "R"})}
