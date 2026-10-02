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

    def step_at(self, turn: int) -> DroneStep:
        """Return this drone's step at the given turn.

        Turns past the drone's last recorded step are clamped to that
        last step: a drone that already reached the goal is no longer
        tracked (subject §VII.5), so its displayed position simply
        stops changing from then on.
        """
        if not self.steps:
            raise ValueError(f"drone {self.drone_id} has no recorded steps")
        index = min(max(turn, 0), len(self.steps) - 1)
        return self.steps[index]
