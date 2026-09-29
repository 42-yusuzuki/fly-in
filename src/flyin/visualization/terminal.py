"""Terminal visualization."""

from flyin.simulation.simulation import Simulation


class TerminalVisualizer:
    """Display Fly-in simulation state in the terminal."""

    def display(self, simulation: Simulation) -> None:
        """Display simulation."""
        raise NotImplementedError
