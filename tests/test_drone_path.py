"""Tests for DronePath.step_at."""

import pytest

from flyin.simulation.drone_path import DronePath, DroneStep


def test_step_at_returns_the_step_for_that_turn() -> None:
    """A mid-path turn returns the exact step recorded for it."""
    path = DronePath(
        drone_id=1,
        steps=[
            DroneStep(turn=0, location="A"),
            DroneStep(turn=1, location="B"),
            DroneStep(turn=2, location="C"),
        ],
    )
    assert path.step_at(1).location == "B"


def test_step_at_clamps_to_the_last_step_once_delivered() -> None:
    """Turns past the drone's last recorded step clamp to that step."""
    path = DronePath(
        drone_id=1,
        steps=[DroneStep(turn=0, location="A"), DroneStep(turn=1, location="goal")],
    )
    assert path.step_at(5).location == "goal"
    assert path.step_at(100).location == "goal"


def test_step_at_clamps_negative_turns_to_zero() -> None:
    """A negative turn clamps to the first recorded step."""
    path = DronePath(drone_id=1, steps=[DroneStep(turn=0, location="A")])
    assert path.step_at(-3).location == "A"


def test_step_at_raises_for_an_empty_path() -> None:
    """A path with no steps has nothing to report at any turn."""
    path = DronePath(drone_id=1, steps=[])
    with pytest.raises(ValueError):
        path.step_at(0)
