"""Time-expanded network models and builder."""

from dataclasses import dataclass

from flyin.domain.map import FlyInMap
from flyin.graph.flow_graph import FlowGraph
from flyin.solver.states import ZoneState


@dataclass
class TimeExpandedNetwork:
    """A flow network expanded along the time axis."""

    graph: FlowGraph
    source: int
    sink: int
    state_to_node: dict[ZoneState, int]
    node_to_state: dict[int, ZoneState]


class TimeExpandedNetworkBuilder:
    """Build a time-expanded flow network from a Fly-in map."""

    def build(
        self,
        flyin_map: FlyInMap,
        max_turns: int,
    ) -> TimeExpandedNetwork:
        """Build a network representing movements up to max_turns."""
        ...