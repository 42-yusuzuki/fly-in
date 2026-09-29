"""Dinic maximum-flow algorithm."""

from flyin.graph.flow_graph import FlowGraph


class Dinic:
    """Maximum-flow solver using Dinic's algorithm."""

    def __init__(self, graph: FlowGraph) -> None:
        """Initialize solver."""
        self.graph = graph

    def max_flow(self, source: int, sink: int) -> int:
        """Calculate maximum flow."""
        raise NotImplementedError
