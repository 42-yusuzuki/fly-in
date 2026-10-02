"""Terminal visualization."""

from flyin.simulation.formatter import SimulationFormatter
from flyin.simulation.simulation import Simulation

_RESET = "\033[0m"
_DRONE_COLORS = (
    "\033[91m",  # red
    "\033[92m",  # green
    "\033[93m",  # yellow
    "\033[94m",  # blue
    "\033[95m",  # magenta
    "\033[96m",  # cyan
)


class TerminalVisualizer:
    """Display Fly-in simulation state in the terminal."""

    def __init__(self, formatter: SimulationFormatter | None = None) -> None:
        """Initialize the visualizer.

        Args:
            formatter: Formatter used to turn the simulation into
                per-turn move lines. Defaults to a plain
                :class:`SimulationFormatter`.
        """
        self._formatter = formatter or SimulationFormatter()

    def display(self, simulation: Simulation) -> None:
        """Display the simulation turn by turn, coloring drones by id."""
        output = self._formatter.format(simulation)

        if not output:
            print("No drone movements were required.")
            return

        print(f"Simulation complete in {simulation.total_turns} turn(s).\n")
        for turn_index, line in enumerate(output.split("\n"), start=1):
            entries = [self._colorize(entry) for entry in line.split()]
            entries_text = " ".join(entries) if entries else "(waiting)"
            print(f"turn {turn_index:>3}: {entries_text}")

    def _colorize(self, entry: str) -> str:
        """Color one 'D<id>-<location>' entry based on its drone id."""
        drone_token = entry.split("-", 1)[0]
        try:
            index = int(drone_token.removeprefix("D")) - 1
        except ValueError:
            index = 0
        color = _DRONE_COLORS[index % len(_DRONE_COLORS)]
        return f"{color}{entry}{_RESET}"
