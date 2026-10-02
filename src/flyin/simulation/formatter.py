"""Subject-compatible simulation output."""

from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation


class SimulationFormatter:
    """Format a simulation using Fly-in output syntax."""

    def format(self, simulation: Simulation) -> str:
        """Format the complete simulation.

        Each simulation turn becomes one line listing every drone
        movement that happened during it, as ``D<id>-<zone>`` (or
        ``D<id>-<connection>`` while in flight toward a restricted
        zone), space-separated. Turns a drone spends waiting in place
        are omitted for that drone, per the subject's output format.
        """
        moves_by_turn: dict[int, list[str]] = {}

        for path in simulation.paths:
            for turn, entry in self._moves(path):
                moves_by_turn.setdefault(turn, []).append(entry)

        if not moves_by_turn:
            return ""

        lines = [
            " ".join(moves_by_turn.get(turn, []))
            for turn in range(1, max(moves_by_turn) + 1)
        ]
        return "\n".join(lines)

    def _moves(self, path: DronePath) -> list[tuple[int, str]]:
        """Return the (turn, 'D<id>-<location>') entries for one drone."""
        moves: list[tuple[int, str]] = []
        previous: DroneStep | None = None

        for step in path.steps:
            if step.turn == 0:
                previous = step
                continue

            moved = (
                step.on_connection
                or previous is None
                or step.location != previous.location
            )
            if moved:
                moves.append((step.turn, f"D{path.drone_id}-{step.location}"))

            previous = step

        return moves
