"""Fly-in simulation representation."""

from dataclasses import dataclass

from flyin.simulation.drone_path import DronePath


@dataclass(frozen=True)
class Simulation:
    """Complete turn-by-turn simulation."""

    paths: list[DronePath]

    @property
    def total_turns(self) -> int:
        """Return total number of simulation turns."""
        if not self.paths:
            return 0

        return max(
            step.turn
            for path in self.paths
            for step in path.steps
        )
