"""Generic residual flow graph."""

from dataclasses import dataclass


@dataclass
class FlowEdge:
    """Residual graph edge."""

    to: int
    rev: int
    capacity: int
    original_capacity: int


class FlowGraph:
    """Directed residual graph."""

    def __init__(self, node_count: int = 0) -> None:
        """Initialize graph with an optional initial node count."""
        self.adjacency: list[list[FlowEdge]] = [
            [] for _ in range(node_count)
        ]

    def add_node(self) -> int:
        """Add a new node to the graph and return its id."""
        self.adjacency.append([])
        return len(self.adjacency) - 1

    def add_edge(self, source: int, target: int, capacity: int) -> None:
        """Add a residual edge pair."""
        forward = FlowEdge(
            to=target,
            rev=len(self.adjacency[target]),
            capacity=capacity,
            original_capacity=capacity,
        )

        reverse = FlowEdge(
            to=source,
            rev=len(self.adjacency[source]),
            capacity=0,
            original_capacity=0,
        )

        self.adjacency[source].append(forward)
        self.adjacency[target].append(reverse)
