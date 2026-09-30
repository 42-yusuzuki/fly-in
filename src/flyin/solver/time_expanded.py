"""Time-expanded network models and builder.

This module translates Fly-in semantics (zone capacity, connection
capacity, restricted-zone transit time) into a plain :class:`FlowGraph`
that knows nothing about drones, zones or turns. :class:`FlowGraph`
and :class:`~flyin.graph.dinic.Dinic` stay fully generic; all Fly-in
specific modelling decisions live here.
"""

from dataclasses import dataclass

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.graph.flow_graph import FlowGraph
from flyin.solver.states import ConnectionState, NodeSide, ZoneState

#: Capacity used for edges that must never be the limiting factor,
#: namely the entry into the start zone and the exit from the goal
#: zone, both of which the Fly-in spec treats as capacity-unlimited.
UNLIMITED_CAPACITY = 10 ** 9

#: A node in the time-expanded network is either a zone state
#: (a drone parked in a zone at a given turn) or a connection state
#: (a drone airborne on a connection at a given turn).
TimeExpandedState = ZoneState | ConnectionState


@dataclass
class TimeExpandedNetwork:
    """A flow network expanded along the time axis."""

    graph: FlowGraph
    source: int
    sink: int
    state_to_node: dict[TimeExpandedState, int]
    node_to_state: dict[int, TimeExpandedState]


class _NodeRegistry:
    """Allocate and cache flow-graph nodes for time-expanded states.

    Every meaningful Fly-in state (a zone at a turn, or a connection
    at a turn) maps to exactly one graph node, created lazily on
    first use. Purely structural helper nodes (connection capacity
    hubs) are allocated directly on the graph and are intentionally
    not tracked here, since they do not correspond to a drone
    position.
    """

    def __init__(self, graph: FlowGraph) -> None:
        """Initialize the registry for a given graph."""
        self._graph = graph
        self.state_to_node: dict[TimeExpandedState, int] = {}
        self.node_to_state: dict[int, TimeExpandedState] = {}

    def node_for(self, state: TimeExpandedState) -> int:
        """Return the node id for a state, creating it if needed."""
        existing = self.state_to_node.get(state)
        if existing is not None:
            return existing

        node = self._graph.add_node()
        self.state_to_node[state] = node
        self.node_to_state[node] = state
        return node


class TimeExpandedNetworkBuilder:
    """Build a time-expanded flow network from a Fly-in map."""

    def build(
        self,
        flyin_map: FlyInMap,
        max_turns: int,
    ) -> TimeExpandedNetwork:
        """Build a network representing movement up to max_turns.

        The network spans turns ``0`` through ``max_turns`` inclusive,
        so a drone may perform at most ``max_turns`` movements
        (a restricted-zone transit counts as two of those movements).

        Args:
            flyin_map: Parsed Fly-in map to model.
            max_turns: Maximum number of simulation turns allowed.

        Returns:
            The constructed time-expanded network. Running max-flow
            from ``network.source`` to ``network.sink`` and comparing
            the result against ``flyin_map.drone_count`` answers
            "can every drone reach the goal within max_turns turns?".
        """
        graph = FlowGraph()
        registry = _NodeRegistry(graph)

        source = graph.add_node()
        sink = graph.add_node()

        self._add_zone_capacity_edges(graph, registry, flyin_map, max_turns)
        self._add_wait_edges(graph, registry, flyin_map, max_turns)

        for connection in flyin_map.connections:
            self._add_connection_gadget(
                graph, registry, flyin_map, connection, max_turns,
            )

        graph.add_edge(
            source,
            registry.node_for(ZoneState(flyin_map.start, 0, NodeSide.IN)),
            flyin_map.drone_count,
        )

        for turn in range(max_turns + 1):
            graph.add_edge(
                registry.node_for(ZoneState(flyin_map.goal, turn, NodeSide.IN)),
                sink,
                UNLIMITED_CAPACITY,
            )

        return TimeExpandedNetwork(
            graph=graph,
            source=source,
            sink=sink,
            state_to_node=registry.state_to_node,
            node_to_state=registry.node_to_state,
        )

    def _zone_capacity(self, flyin_map: FlyInMap, zone: Zone) -> int:
        """Return the effective capacity of a zone at a single turn."""
        if zone.name in (flyin_map.start, flyin_map.goal):
            return UNLIMITED_CAPACITY
        return zone.max_drones

    def _add_zone_capacity_edges(
        self,
        graph: FlowGraph,
        registry: _NodeRegistry,
        flyin_map: FlyInMap,
        max_turns: int,
    ) -> None:
        """Add the vertex-split IN -> OUT edge that enforces max_drones."""
        for zone in flyin_map.zones.values():
            if zone.zone_type == ZoneType.BLOCKED:
                continue

            capacity = self._zone_capacity(flyin_map, zone)

            for turn in range(max_turns + 1):
                zone_in = registry.node_for(ZoneState(zone.name, turn, NodeSide.IN))
                zone_out = registry.node_for(ZoneState(zone.name, turn, NodeSide.OUT))
                graph.add_edge(zone_in, zone_out, capacity)

    def _add_wait_edges(
        self,
        graph: FlowGraph,
        registry: _NodeRegistry,
        flyin_map: FlyInMap,
        max_turns: int,
    ) -> None:
        """Add OUT@t -> IN@(t+1) edges allowing a drone to wait in place."""
        for zone in flyin_map.zones.values():
            if zone.zone_type == ZoneType.BLOCKED:
                continue

            capacity = self._zone_capacity(flyin_map, zone)

            for turn in range(max_turns):
                zone_out = registry.node_for(ZoneState(zone.name, turn, NodeSide.OUT))
                next_in = registry.node_for(
                    ZoneState(zone.name, turn + 1, NodeSide.IN)
                )
                graph.add_edge(zone_out, next_in, capacity)

    def _add_connection_gadget(
        self,
        graph: FlowGraph,
        registry: _NodeRegistry,
        flyin_map: FlyInMap,
        connection: Connection,
        max_turns: int,
    ) -> None:
        """Add the shared-capacity gadget for one bidirectional connection.

        For every turn a shared bottleneck edge (the "hub") caps the
        combined number of drones crossing the connection in *either*
        direction during that turn to ``connection.max_capacity``:

            source_out@t --\\                       /--> dest lane
                             hub_in --(cap M)--> hub_out
              dest_out@t --/                       \\--> source lane

        Each direction then continues on its own lane to its own
        destination, so the destination a drone lands on is never
        ambiguous downstream of the hub; the hub only shares *how
        much* capacity is available, never *where* a drone ends up.
        """
        source_zone = flyin_map.zones[connection.source]
        dest_zone = flyin_map.zones[connection.destination]

        if (
            source_zone.zone_type == ZoneType.BLOCKED
            or dest_zone.zone_type == ZoneType.BLOCKED
        ):
            return

        for turn in range(max_turns):
            hub_in = graph.add_node()
            hub_out = graph.add_node()
            graph.add_edge(hub_in, hub_out, connection.max_capacity)

            graph.add_edge(
                registry.node_for(ZoneState(source_zone.name, turn, NodeSide.OUT)),
                hub_in,
                connection.max_capacity,
            )
            graph.add_edge(
                registry.node_for(ZoneState(dest_zone.name, turn, NodeSide.OUT)),
                hub_in,
                connection.max_capacity,
            )

            self._add_transit_lane(
                graph,
                registry,
                connection,
                hub_out,
                destination=dest_zone,
                depart_turn=turn,
                max_turns=max_turns,
            )
            self._add_transit_lane(
                graph,
                registry,
                connection,
                hub_out,
                destination=source_zone,
                depart_turn=turn,
                max_turns=max_turns,
            )

    def _add_transit_lane(
        self,
        graph: FlowGraph,
        registry: _NodeRegistry,
        connection: Connection,
        hub_out: int,
        destination: Zone,
        depart_turn: int,
        max_turns: int,
    ) -> None:
        """Wire one direction's lane from the hub to its destination.

        A restricted destination requires an explicit
        :class:`ConnectionState` node for the airborne turn; a normal
        or priority destination is reached directly on the next turn.
        Either way the lane has a single onward edge, so a drone that
        starts a transit is committed to arriving at ``destination``
        and cannot wait mid-connection.
        """
        if destination.zone_type == ZoneType.RESTRICTED:
            arrival_turn = depart_turn + 2
            if arrival_turn > max_turns:
                return

            mid_turn = depart_turn + 1
            mid_node = registry.node_for(
                ConnectionState(connection.connection_id, mid_turn, destination.name)
            )
            arrival_state = ZoneState(destination.name, arrival_turn, NodeSide.IN)
            graph.add_edge(hub_out, mid_node, connection.max_capacity)
            graph.add_edge(
                mid_node,
                registry.node_for(arrival_state),
                connection.max_capacity,
            )
        else:
            arrival_turn = depart_turn + 1
            if arrival_turn > max_turns:
                return

            arrival_state = ZoneState(destination.name, arrival_turn, NodeSide.IN)
            graph.add_edge(
                hub_out,
                registry.node_for(arrival_state),
                connection.max_capacity,
            )
