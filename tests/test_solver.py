"""Tests for the end-to-end Fly-in solver."""

import pytest

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.solver.errors import FlyInSolutionError
from flyin.solver.solver import FlyInSolver


def _zone(
    name: str,
    zone_type: ZoneType = ZoneType.NORMAL,
    max_drones: int = 10,
) -> Zone:
    return Zone(name=name, x=0, y=0, zone_type=zone_type, max_drones=max_drones)


def test_single_drone_direct_connection_takes_one_turn() -> None:
    """A -> B with one drone should resolve in exactly one turn."""
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )

    solution = FlyInSolver().solve(flyin_map)

    assert solution.turns == 1
    assert len(solution.paths) == 1
    assert [step.location for step in solution.paths[0].steps] == ["A", "B"]


def test_zero_drones_resolves_in_zero_turns() -> None:
    """A map with no drones to route needs no turns and no paths."""
    flyin_map = FlyInMap(
        drone_count=0,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )

    solution = FlyInSolver().solve(flyin_map)

    assert solution.turns == 0
    assert solution.paths == []


def test_bottleneck_zone_forces_drones_to_queue() -> None:
    """A capacity-1 middle zone must serialize two drones across 2 turns."""
    flyin_map = FlyInMap(
        drone_count=2,
        start="A",
        goal="C",
        zones={
            "A": _zone("A"),
            "B": _zone("B", max_drones=1),
            "C": _zone("C"),
        },
        connections=[
            Connection(1, "A", "B", max_capacity=5),
            Connection(2, "B", "C", max_capacity=5),
        ],
    )

    solution = FlyInSolver().solve(flyin_map)

    assert solution.turns == 3
    assert len(solution.paths) == 2
    for path in solution.paths:
        assert [step.location for step in path.steps][-1] == "C"


def test_restricted_zone_costs_two_turns_in_flight() -> None:
    """Entering a restricted zone must show one in-flight turn, then arrival."""
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="R",
        zones={"A": _zone("A"), "R": _zone("R", zone_type=ZoneType.RESTRICTED)},
        connections=[Connection(1, "A", "R", max_capacity=5)],
    )

    solution = FlyInSolver().solve(flyin_map)

    assert solution.turns == 2
    steps = solution.paths[0].steps
    assert [(step.turn, step.location, step.on_connection) for step in steps] == [
        (0, "A", False),
        (1, "A-R", True),
        (2, "R", False),
    ]


def test_unreachable_goal_raises_solution_error() -> None:
    """A goal with no connection to the start must raise, not hang."""
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[],
    )

    with pytest.raises(FlyInSolutionError):
        FlyInSolver(max_turns_cap=8).solve(flyin_map)
