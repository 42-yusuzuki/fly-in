"""Capacity reports for the zone or connection selected in the visualizer.

Reports are derived from the presentation model and one turn snapshot;
they hold no Textual types, so the inspector widget only formats them.
"""

from dataclasses import dataclass

from flyin.visualization.tui.model import VisualConnection, VisualMap, VisualZone
from flyin.visualization.tui.snapshot import DroneSnapshot, TurnSnapshot, link_key

Selectable = VisualZone | VisualConnection


def selectables(visual_map: VisualMap) -> tuple[Selectable, ...]:
    """Return what Tab cycles through: every zone, then every connection."""
    return (*visual_map.zones, *visual_map.connections)


@dataclass(frozen=True)
class LinkLoad:
    """How busy one connection is at a turn.

    Attributes:
        connection: The connection.
        drones: Drones counted against its capacity this turn (see
            :meth:`TurnSnapshot.link_usage`).
        landing: Drones finishing a restricted transit over it this
            turn; shown for context but not counted.
    """

    connection: VisualConnection
    drones: tuple[DroneSnapshot, ...]
    landing: tuple[DroneSnapshot, ...] = ()

    @property
    def occupancy(self) -> int:
        """Return how many drones use the connection this turn."""
        return len(self.drones)

    @property
    def full(self) -> bool:
        """Return whether the link capacity is reached."""
        return self.occupancy >= self.connection.max_capacity


@dataclass(frozen=True)
class ZoneReport:
    """Occupancy of one zone and its connections at a turn."""

    zone: VisualZone
    drones: tuple[DroneSnapshot, ...]
    links: tuple[LinkLoad, ...]

    @property
    def occupancy(self) -> int:
        """Return how many drones sit on the zone this turn."""
        return len(self.drones)

    @property
    def full(self) -> bool:
        """Return whether a capacity-limited zone is at capacity."""
        limit = self.zone.max_drones
        return limit is not None and self.occupancy >= limit


def link_load(
    connection: VisualConnection, snapshot: TurnSnapshot,
) -> LinkLoad:
    """Return how busy ``connection`` is at ``snapshot``."""
    key = link_key(connection.zone_a, connection.zone_b)
    return LinkLoad(
        connection,
        snapshot.link_usage().get(key, ()),
        snapshot.landings().get(key, ()),
    )


def zone_report(
    visual_map: VisualMap, zone: VisualZone, snapshot: TurnSnapshot,
) -> ZoneReport:
    """Return the occupancy of ``zone`` and its connections at a turn."""
    return ZoneReport(
        zone=zone,
        drones=snapshot.drones_at(zone.name),
        links=tuple(
            link_load(connection, snapshot)
            for connection in visual_map.connections_of(zone.name)
        ),
    )
