"""Subject-compatible simulation output."""

from flyin.simulation.simulation import Simulation


class SimulationFormatter:
    """Format a simulation using Fly-in output syntax."""

    def format(self, simulation: Simulation) -> str:
        """Format the complete simulation."""
        raise NotImplementedError
