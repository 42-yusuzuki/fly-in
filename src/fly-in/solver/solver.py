"""High-level Fly-in solver."""

from flyin.domain.map import FlyInMap
from flyin.solver.solution import Solution


class FlyInSolver:
    """Find a minimum-turn solution for all drones."""

    def solve(self, flyin_map: FlyInMap) -> Solution:
        """Solve a Fly-in map."""
        raise NotImplementedError
