"""Drone route models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DroneStep:
    """One drone state during a simulation turn."""

    turn: int
    location: str
    on_connection: bool = False


@dataclass(frozen=True)
class DronePath:
    """Path assigned to one drone."""

    drone_id: int
    steps: list[DroneStep]
