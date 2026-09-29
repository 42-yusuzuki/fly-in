"""Convert network flow into individual drone paths."""

from flyin.graph.flow_graph import FlowGraph
from flyin.simulation.drone_path import DronePath


class FlowDecomposer:
    """Decompose integral flow into individual drone routes."""

    def decompose(
        self,
        graph: FlowGraph,
        source: int,
        sink: int,
        drone_count: int,
    ) -> list[DronePath]:
        """Extract one path for each drone."""
        raise NotImplementedError
