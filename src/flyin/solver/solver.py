"""High-level Fly-in solver."""

from flyin.domain.map import FlyInMap
from flyin.graph.dinic import Dinic
from flyin.solver.decomposer import FlowDecomposer
from flyin.solver.errors import FlyInSolutionError
from flyin.solver.solution import Solution
from flyin.solver.time_expanded import TimeExpandedNetworkBuilder


class FlyInSolver:
    """Find a minimum-turn solution for all drones.

    The search relies on a monotonicity property of the time-expanded
    network: every edge present when building the network for ``T``
    turns is still present, with the same capacity, when building it
    for any ``T' > T``. The maximum achievable flow is therefore
    non-decreasing in the number of turns, which makes a doubling
    search for an upper bound followed by a binary search for the
    minimum both correct and efficient.
    """

    def __init__(self, max_turns_cap: int = 1000) -> None:
        """Initialize the solver.

        Args:
            max_turns_cap: Hard ceiling on the number of turns to try
                before concluding that no routing exists.
        """
        self._max_turns_cap = max_turns_cap
        self._builder = TimeExpandedNetworkBuilder()

    def solve(self, flyin_map: FlyInMap) -> Solution:
        """Solve a Fly-in map."""
        if flyin_map.drone_count == 0:
            return Solution(turns=0, paths=[])

        best_turns = self._find_minimum_turns(flyin_map)

        network = self._builder.build(flyin_map, best_turns)
        Dinic(network.graph).max_flow(network.source, network.sink)
        paths = FlowDecomposer().decompose(network, flyin_map)

        return Solution(turns=best_turns, paths=paths)

    def _max_flow_at(self, flyin_map: FlyInMap, max_turns: int) -> int:
        """Return the maximum number of drones routable within max_turns."""
        network = self._builder.build(flyin_map, max_turns)
        return Dinic(network.graph).max_flow(network.source, network.sink)

    def _find_minimum_turns(self, flyin_map: FlyInMap) -> int:
        """Find the minimum turn count that routes every drone."""
        upper = 1
        while self._max_flow_at(flyin_map, upper) < flyin_map.drone_count:
            if upper >= self._max_turns_cap:
                raise FlyInSolutionError(
                    "no routing found for all drones within "
                    f"{self._max_turns_cap} turns"
                )
            upper *= 2

        lower = upper // 2
        while lower < upper:
            mid = (lower + upper) // 2
            if self._max_flow_at(flyin_map, mid) >= flyin_map.drone_count:
                upper = mid
            else:
                lower = mid + 1

        return upper
