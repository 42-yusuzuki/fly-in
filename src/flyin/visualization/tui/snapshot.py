"""Per-turn drone snapshots derived from a :class:`Simulation`.

A snapshot describes where every drone is at one logical turn and what
it did to get there (waited, moved, entered a restricted transit, ...).
Snapshots are plain data with no Textual types, so the renderer and the
status panel can both consume them, and they are built once up front so
stepping between turns never re-derives anything.
"""

from dataclasses import dataclass
from enum import Enum

from flyin.simulation.drone_path import DronePath
from flyin.simulation.simulation import Simulation


class DroneActivity(Enum):
    """What a drone did during the turn that ended at a snapshot.

    The values partition the fleet: every drone has exactly one.
    """

    WAITING = "waiting"
    MOVING = "moving"
    IN_TRANSIT = "in transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"


@dataclass(frozen=True)
class DroneSnapshot:
    """One drone's state at one turn.

    Attributes:
        drone_id: Drone number, as in the simulation output.
        activity: What the drone did during this turn.
        zone: Zone the drone occupies, or ``None`` while it is in
            transit on a connection.
        source: Zone the drone left to make this turn's move (for a
            drone landing after a restricted transit, the zone it left
            two turns ago), or ``None`` if it did not move.
        target: Zone the drone is heading to or just reached, or
            ``None`` if it did not move.
    """

    drone_id: int
    activity: DroneActivity
    zone: str | None
    source: str | None = None
    target: str | None = None

    @property
    def link(self) -> tuple[str, str] | None:
        """Return the ``(source, target)`` connection used this turn."""
        if self.source is None or self.target is None:
            return None
        return self.source, self.target

    @property
    def on_map(self) -> bool:
        """Return whether the drone is still drawn on the graph.

        Drones delivered on an earlier turn are no longer tracked
        (subject §VII.5) and disappear from the graph; they only remain
        in the delivered count.
        """
        return self.activity is not DroneActivity.DELIVERED


@dataclass(frozen=True)
class TurnSnapshot:
    """Every drone's state at one logical turn."""

    turn: int
    drones: tuple[DroneSnapshot, ...]

    def count(self, *activities: DroneActivity) -> int:
        """Return how many drones have any of the given activities."""
        return sum(1 for drone in self.drones if drone.activity in activities)

    @property
    def delivered_count(self) -> int:
        """Return how many drones have reached the end zone so far."""
        return self.count(DroneActivity.ARRIVED, DroneActivity.DELIVERED)

    def drones_at(self, zone: str) -> tuple[DroneSnapshot, ...]:
        """Return the drones drawn on ``zone`` at this turn."""
        return tuple(
            drone for drone in self.drones
            if drone.on_map and drone.zone == zone
        )

    def in_transit(self) -> tuple[DroneSnapshot, ...]:
        """Return the drones that are on a connection at this turn."""
        return tuple(
            drone for drone in self.drones
            if drone.activity is DroneActivity.IN_TRANSIT
        )

    def transit_groups(self) -> dict[tuple[str, str], tuple[DroneSnapshot, ...]]:
        """Group this turn's in-transit drones by connection."""
        return group_by_link(self.in_transit())

    def movers(self) -> tuple[DroneSnapshot, ...]:
        """Return the drones that used a connection during this turn."""
        return tuple(drone for drone in self.drones if drone.link is not None)

    def used_links(self) -> frozenset[frozenset[str]]:
        """Return the connections used this turn, as unordered pairs."""
        return frozenset(
            frozenset(drone.link)
            for drone in self.drones if drone.link is not None
        )


def group_by_link(
    drones: tuple[DroneSnapshot, ...],
) -> dict[tuple[str, str], tuple[DroneSnapshot, ...]]:
    """Group drones by the connection they use, in either direction.

    Keys are the connection's endpoints in sorted order, so drones
    crossing the same connection in opposite directions share a group
    (they share a single drawn edge too). Drones without a link are
    skipped.
    """
    groups: dict[tuple[str, str], list[DroneSnapshot]] = {}
    for drone in drones:
        if drone.link is not None:
            key = (min(drone.link), max(drone.link))
            groups.setdefault(key, []).append(drone)
    return {key: tuple(members) for key, members in groups.items()}


def build_snapshots(simulation: Simulation, goal: str) -> tuple[TurnSnapshot, ...]:
    """Return one snapshot per turn, from turn 0 to the last turn.

    Args:
        simulation: Solved simulation to replay. It is only read.
        goal: Name of the end zone.

    Raises:
        ValueError: If a path ends while its drone is on a connection.
    """
    return tuple(
        TurnSnapshot(
            turn=turn,
            drones=tuple(_drone_at(path, turn, goal) for path in simulation.paths),
        )
        for turn in range(simulation.total_turns + 1)
    )


def _drone_at(path: DronePath, turn: int, goal: str) -> DroneSnapshot:
    """Classify one drone's state at ``turn``.

    ``DronePath.steps`` holds one step per turn starting at turn 0, and
    a restricted transit is a single ``on_connection`` step between the
    origin zone and the landing zone.
    """
    step = path.step_at(turn)
    drone_id = path.drone_id

    if step.on_connection:
        if turn + 1 >= len(path.steps):
            raise ValueError(
                f"drone {drone_id} ends its path on connection {step.location}"
            )
        return DroneSnapshot(
            drone_id=drone_id,
            activity=DroneActivity.IN_TRANSIT,
            zone=None,
            source=path.step_at(turn - 1).location,
            target=path.step_at(turn + 1).location,
        )

    previous = path.step_at(turn - 1) if turn > 0 else None
    if previous is None or (
        not previous.on_connection and previous.location == step.location
    ):
        activity = (
            DroneActivity.DELIVERED if step.location == goal
            else DroneActivity.WAITING
        )
        return DroneSnapshot(drone_id, activity, step.location)

    source = (
        path.step_at(turn - 2).location if previous.on_connection
        else previous.location
    )
    return DroneSnapshot(
        drone_id=drone_id,
        activity=(
            DroneActivity.ARRIVED if step.location == goal
            else DroneActivity.MOVING
        ),
        zone=step.location,
        source=source,
        target=step.location,
    )
