"""Dinic maximum-flow algorithm."""

from collections import deque

from flyin.graph.flow_graph import FlowGraph


class Dinic:
    """Maximum-flow solver using Dinic's algorithm."""

    def __init__(self, graph: FlowGraph) -> None:
        """Initialize solver."""
        self.graph = graph
        self.level: list[int] = []
        self.iteration: list[int] = []

    def max_flow(self, source: int, sink: int) -> int:
        """Calculate maximum flow."""
        flow = 0

        while self._build_level_graph(source, sink):
            self.iteration = [0] * len(self.graph.adjacency)

            while True:
                pushed = self._send_flow(
                    source,
                    sink,
                    10**18,
                )

                if pushed == 0:
                    break

                flow += pushed

        return flow

    def _build_level_graph(self, source: int, sink: int) -> bool:
        """Build a level graph using BFS."""
        node_count = len(self.graph.adjacency)
        self.level = [-1] * node_count

        queue: deque[int] = deque([source])
        self.level[source] = 0

        while queue:
            node = queue.popleft()

            for edge in self.graph.adjacency[node]:
                if edge.capacity <= 0:
                    continue

                if self.level[edge.to] != -1:
                    continue

                self.level[edge.to] = self.level[node] + 1
                queue.append(edge.to)

        return self.level[sink] != -1

    def _send_flow(
        self,
        node: int,
        sink: int,
        flow: int,
    ) -> int:
        """Send blocking flow through the level graph."""
        if node == sink:
            return flow

        while self.iteration[node] < len(self.graph.adjacency[node]):
            edge_index = self.iteration[node]
            edge = self.graph.adjacency[node][edge_index]

            if (
                edge.capacity > 0
                and self.level[edge.to] == self.level[node] + 1
            ):
                pushed = self._send_flow(
                    edge.to,
                    sink,
                    min(flow, edge.capacity),
                )

                if pushed > 0:
                    edge.capacity -= pushed

                    reverse = self.graph.adjacency[edge.to][edge.rev]
                    reverse.capacity += pushed

                    return pushed

            self.iteration[node] += 1

        return 0
