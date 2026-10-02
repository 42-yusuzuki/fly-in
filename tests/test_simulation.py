"""Tests for simulation/output."""

from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation


def test_total_turns_is_zero_for_no_paths() -> None:
    """An empty simulation has no turns."""
    assert Simulation(paths=[]).total_turns == 0


def test_total_turns_is_the_latest_step_across_all_drones() -> None:
    """total_turns must be the maximum turn across every drone's steps."""
    simulation = Simulation(
        paths=[
            DronePath(
                drone_id=1,
                steps=[
                    DroneStep(turn=0, location="a"),
                    DroneStep(turn=2, location="b"),
                ],
            ),
            DronePath(
                drone_id=2,
                steps=[
                    DroneStep(turn=0, location="a"),
                    DroneStep(turn=5, location="c"),
                ],
            ),
        ]
    )
    assert simulation.total_turns == 5
