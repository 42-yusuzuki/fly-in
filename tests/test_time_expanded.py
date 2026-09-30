"""Tests for the time-expanded network."""

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.graph.dinic import Dinic
from flyin.solver.states import ConnectionState, NodeSide, ZoneState
from flyin.solver.time_expanded import TimeExpandedNetworkBuilder


def _zone(
    name: str,
    zone_type: ZoneType = ZoneType.NORMAL,
    max_drones: int = 10,
) -> Zone:
    return Zone(name=name, x=0, y=0, zone_type=zone_type, max_drones=max_drones)


def _max_flow(flyin_map: FlyInMap, max_turns: int) -> int:
    network = TimeExpandedNetworkBuilder().build(flyin_map, max_turns)
    return Dinic(network.graph).max_flow(network.source, network.sink)


def test_normal_movement_reaches_next_turn() -> None:
    """A -> B (B normal) should be flyable in a single turn."""
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )

    assert _max_flow(flyin_map, max_turns=0) == 0
    assert _max_flow(flyin_map, max_turns=1) == 1


def test_restricted_movement_requires_two_turns() -> None:
    """A -> R (R restricted) must take 2 turns, never 1."""
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="R",
        zones={
            "A": _zone("A"),
            "R": _zone("R", zone_type=ZoneType.RESTRICTED),
        },
        connections=[Connection(1, "A", "R", max_capacity=5)],
    )

    assert _max_flow(flyin_map, max_turns=1) == 0
    assert _max_flow(flyin_map, max_turns=2) == 1

    network = TimeExpandedNetworkBuilder().build(flyin_map, max_turns=2)
    connection_states = [
        state
        for state in network.state_to_node
        if isinstance(state, ConnectionState)
    ]
    assert len(connection_states) == 1
    assert connection_states[0].turn == 1
    assert connection_states[0].destination == "R"


def test_connection_capacity_limits_same_turn_crossings() -> None:
    """max_link_capacity=1 must stop 2 drones crossing in the same turn."""
    flyin_map = FlyInMap(
        drone_count=2,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[Connection(1, "A", "B", max_capacity=1)],
    )

    assert _max_flow(flyin_map, max_turns=1) == 1


def test_connection_capacity_shared_across_both_directions() -> None:
    """capacity=1 must not allow A->B and B->A at the same turn."""
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[Connection(1, "A", "B", max_capacity=1)],
    )

    network = TimeExpandedNetworkBuilder().build(flyin_map, max_turns=1)
    graph = network.graph

    a_out = network.state_to_node[ZoneState("A", 0, NodeSide.OUT)]
    b_out = network.state_to_node[ZoneState("B", 0, NodeSide.OUT)]
    a_in_next = network.state_to_node[ZoneState("A", 1, NodeSide.IN)]
    b_in_next = network.state_to_node[ZoneState("B", 1, NodeSide.IN)]

    # A plain end-to-end max-flow check cannot isolate this: B's own
    # "wait in place" edge (B_out@0 -> B_in@1) is a legitimate,
    # unrelated way to occupy the exact node a naive A -> B probe
    # would sink into, so a flow-value assertion would pass even if
    # capacity were *not* shared. Inspect the gadget's structure
    # directly instead: both directions must enter through the same
    # single bottleneck edge before they are allowed to diverge.
    a_targets = {e.to for e in graph.adjacency[a_out] if e.capacity > 0}
    b_targets = {e.to for e in graph.adjacency[b_out] if e.capacity > 0}
    shared = a_targets & b_targets

    assert len(shared) == 1
    hub_in = shared.pop()

    hub_forward_edges = [
        e for e in graph.adjacency[hub_in] if e.capacity > 0
    ]
    assert len(hub_forward_edges) == 1

    bottleneck = hub_forward_edges[0]
    assert bottleneck.capacity == 1  # == max_link_capacity, shared total
    hub_out = bottleneck.to

    exits = {e.to for e in graph.adjacency[hub_out] if e.capacity > 0}
    assert exits == {a_in_next, b_in_next}


def test_connection_capacity_two_allows_two_drones() -> None:
    """capacity=2 should let 2 drones cross in the same turn."""
    flyin_map = FlyInMap(
        drone_count=2,
        start="A",
        goal="B",
        zones={"A": _zone("A"), "B": _zone("B")},
        connections=[Connection(1, "A", "B", max_capacity=2)],
    )

    assert _max_flow(flyin_map, max_turns=1) == 2


def test_restricted_transit_respects_destination_capacity() -> None:
    """A restricted transit must not overfill its destination zone."""
    flyin_map = FlyInMap(
        drone_count=2,
        start="A",
        goal="G",
        zones={
            "A": _zone("A"),
            "R": _zone("R", zone_type=ZoneType.RESTRICTED, max_drones=1),
            "G": _zone("G"),
        },
        connections=[
            Connection(1, "A", "R", max_capacity=5),
            Connection(2, "R", "G", max_capacity=5),
        ],
    )

    # The earliest full journey (A -> R restricted transit, then
    # R -> G) takes 3 turns. Both drones can only depart A at turn 0,
    # so they would land in R at turn 2 together; R's capacity of 1
    # must block the second one from even starting the transit, so
    # only 1 drone can finish within 3 turns.
    assert _max_flow(flyin_map, max_turns=3) == 1

    # Given a 4th turn, the second drone can wait one turn in A,
    # depart later, and land in R at turn 3 instead (a separate,
    # unfilled per-turn capacity slot) before continuing to G.
    assert _max_flow(flyin_map, max_turns=4) == 2


def test_waiting_in_a_normal_zone() -> None:
    """A drone should be able to wait in place: B@t -> B@(t+1).

    B -> G only has capacity 1, so with 2 drones the second one must
    wait a turn in B before it can cross; it only makes it to G if
    max_turns leaves room for that wait.
    """
    flyin_map = FlyInMap(
        drone_count=2,
        start="A",
        goal="G",
        zones={"A": _zone("A"), "B": _zone("B", max_drones=3), "G": _zone("G")},
        connections=[
            Connection(1, "A", "B", max_capacity=5),
            Connection(2, "B", "G", max_capacity=1),
        ],
    )

    assert _max_flow(flyin_map, max_turns=2) == 1
    assert _max_flow(flyin_map, max_turns=3) == 2

    network = TimeExpandedNetworkBuilder().build(flyin_map, max_turns=3)
    wait_edge_capacities = [
        edge.original_capacity
        for edge in network.graph.adjacency[
            network.state_to_node[ZoneState("B", 1, NodeSide.OUT)]
        ]
        if edge.to == network.state_to_node[ZoneState("B", 2, NodeSide.IN)]
    ]
    assert wait_edge_capacities == [3]  # B's own max_drones, not unlimited
