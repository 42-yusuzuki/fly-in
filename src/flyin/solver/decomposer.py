"""Convert network flow into individual drone paths."""

from flyin.domain.map import FlyInMap
from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.solver.states import ConnectionState, NodeSide, ZoneState
from flyin.solver.time_expanded import TimeExpandedNetwork, TimeExpandedState


class FlowDecomposer:
    """Decompose integral flow into individual drone routes."""

    def decompose(
        self,
        network: TimeExpandedNetwork,
        flyin_map: FlyInMap,
    ) -> list[DronePath]:
        """Extract one path for each drone from a solved flow network.

        Args:
            network: Time-expanded network whose graph has already had
                max-flow computed on it (``network.graph`` residual
                capacities encode how much flow crosses each edge).
            flyin_map: The map the network was built from, used to
                recover human-readable connection labels and the goal
                zone name.

        Returns:
            One path per drone, in drone-id order.
        """
        connection_labels = {
            connection.connection_id: f"{connection.source}-{connection.destination}"
            for connection in flyin_map.connections
        }

        paths: list[DronePath] = []
        for drone_id in range(1, flyin_map.drone_count + 1):
            node_path = self._extract_one_path(network)
            steps = self._to_steps(
                node_path, network.node_to_state, connection_labels, flyin_map.goal,
            )
            paths.append(DronePath(drone_id=drone_id, steps=steps))
        return paths

    def _extract_one_path(self, network: TimeExpandedNetwork) -> list[int]:
        """Peel one unit-flow path from source to sink off the graph.

        The time-expanded network is a DAG (every edge strictly
        advances turn, or moves within a single helper gadget that has
        no back edge), so a greedy walk that always follows an edge
        still carrying flow is guaranteed to terminate at the sink
        without visiting any node twice.
        """
        graph = network.graph
        path = [network.source]
        node = network.source

        while node != network.sink:
            for edge in graph.adjacency[node]:
                flow = edge.original_capacity - edge.capacity
                if flow > 0:
                    edge.capacity += 1
                    path.append(edge.to)
                    node = edge.to
                    break
            else:
                raise RuntimeError(
                    "flow decomposition failed: no outgoing flow at node "
                    f"{node} (network must have max-flow computed first)"
                )

        return path

    def _to_steps(
        self,
        node_path: list[int],
        node_to_state: dict[int, TimeExpandedState],
        connection_labels: dict[int, str],
        goal: str,
    ) -> list[DroneStep]:
        """Translate a raw node-id path into drone steps.

        Structural helper nodes (source, sink, connection-capacity
        hubs) carry no state and are skipped. Only the IN side of a
        zone is reported, since IN and OUT represent the same zone at
        the same turn. Collection stops as soon as the goal zone is
        reached, since delivered drones are no longer tracked.
        """
        steps: list[DroneStep] = []
        for node in node_path:
            state = node_to_state.get(node)
            if state is None:
                continue

            if isinstance(state, ZoneState):
                if state.side != NodeSide.IN:
                    continue
                steps.append(DroneStep(turn=state.turn, location=state.zone_name))
                if state.zone_name == goal:
                    break
            elif isinstance(state, ConnectionState):
                steps.append(
                    DroneStep(
                        turn=state.turn,
                        location=connection_labels[state.connection_id],
                        on_connection=True,
                    )
                )

        return steps
