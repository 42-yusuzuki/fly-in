"""Construction of the Fly-in time-expanded network."""

from dataclasses import dataclass

from flyin.domain.map import FlyInMap
from flyin.graph.flow_graph import FlowGraph


@dataclass
class TimeExpandedNetwork:
    """Generated flow network with source/sink metadata."""

    graph: FlowGraph
    source: int
    sink: int


class TimeExpandedNetworkBuilder:
    """Translate a Fly-in map into a time-expanded flow network."""

    def build(
        self,
        flyin_map: FlyInMap,
        max_turns: int,
    ) -> TimeExpandedNetwork:
        """Build the network for a fixed time horizon."""
        raise NotImplementedError
