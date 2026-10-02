"""Tests for simulation/output."""

from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.formatter import SimulationFormatter
from flyin.simulation.simulation import Simulation


def test_empty_simulation_formats_to_empty_string() -> None:
    """A simulation with no paths should format to an empty string."""
    assert SimulationFormatter().format(Simulation(paths=[])) == ""


def test_waiting_turns_are_omitted() -> None:
    """A drone that stays in the same zone must not appear that turn."""
    path = DronePath(
        drone_id=1,
        steps=[
            DroneStep(turn=0, location="start"),
            DroneStep(turn=1, location="start"),  # waited
            DroneStep(turn=2, location="goal"),
        ],
    )
    output = SimulationFormatter().format(Simulation(paths=[path]))
    assert output == "\nD1-goal"


def test_two_drones_interleave_by_turn() -> None:
    """Movements from different drones on the same turn share a line."""
    d1 = DronePath(
        drone_id=1,
        steps=[
            DroneStep(turn=0, location="start"),
            DroneStep(turn=1, location="a"),
            DroneStep(turn=2, location="goal"),
        ],
    )
    d2 = DronePath(
        drone_id=2,
        steps=[
            DroneStep(turn=0, location="start"),
            DroneStep(turn=1, location="goal"),
        ],
    )
    output = SimulationFormatter().format(Simulation(paths=[d1, d2]))
    assert output == "D1-a D2-goal\nD1-goal"


def test_connection_transit_uses_connection_label() -> None:
    """An in-flight step must always be reported, labeled by connection."""
    path = DronePath(
        drone_id=1,
        steps=[
            DroneStep(turn=0, location="start"),
            DroneStep(turn=1, location="start-restricted", on_connection=True),
            DroneStep(turn=2, location="restricted"),
        ],
    )
    output = SimulationFormatter().format(Simulation(paths=[path]))
    assert output == "D1-start-restricted\nD1-restricted"
