"""Presentation models for the terminal visualizer.

These are read-only views derived from :class:`FlyInMap`. They carry no
Textual types and no rendering state, so the same models can feed a
simpler ANSI/curses renderer if Textual is ever dropped.
"""

from dataclasses import dataclass
from enum import Enum

from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType


class ZoneRole(Enum):
    """Role a zone plays in the map, independent of its zone type."""

    START = "start"
    END = "end"
    HUB = "hub"


@dataclass(frozen=True)
class VisualZone:
    """Display data for one zone.

    Attributes:
        name: Zone name, unique within the map.
        world_x: Integer x coordinate from the map file.
        world_y: Integer y coordinate from the map file.
        zone_type: Zone type from the map file.
        role: Whether the zone is the start, the end, or a plain hub.
        max_drones: Effective capacity, or ``None`` when unlimited
            (start and end zones, per the subject).
        color: Raw color metadata from the map file, if any.
    """

    name: str
    world_x: int
    world_y: int
    zone_type: ZoneType
    role: ZoneRole
    max_drones: int | None
    color: str | None


@dataclass(frozen=True)
class VisualConnection:
    """Display data for one bidirectional connection."""

    zone_a: str
    zone_b: str
    max_capacity: int

    @property
    def label(self) -> str:
        """Return a human-readable ``A <-> B`` label."""
        return f"{self.zone_a} <-> {self.zone_b}"


@dataclass(frozen=True)
class WorldBounds:
    """Inclusive bounding box of all zone coordinates in map space."""

    min_x: int
    max_x: int
    min_y: int
    max_y: int


@dataclass(frozen=True)
class VisualMap:
    """Static, renderer-agnostic view of a parsed Fly-in map."""

    title: str
    drone_count: int
    zones: tuple[VisualZone, ...]
    connections: tuple[VisualConnection, ...]
    bounds: WorldBounds

    @classmethod
    def from_flyin_map(cls, flyin_map: FlyInMap, title: str) -> "VisualMap":
        """Build a presentation model from a parsed map.

        Args:
            flyin_map: Parsed map to display. It is only read.
            title: Short name shown in the UI (typically the file name).

        Raises:
            ValueError: If the map has no zones.
        """
        if not flyin_map.zones:
            raise ValueError("cannot visualize a map without zones")

        zones = tuple(
            _visual_zone(zone, flyin_map)
            for zone in flyin_map.zones.values()
        )
        connections = tuple(
            VisualConnection(
                zone_a=connection.source,
                zone_b=connection.destination,
                max_capacity=connection.max_capacity,
            )
            for connection in flyin_map.connections
        )
        xs = [zone.world_x for zone in zones]
        ys = [zone.world_y for zone in zones]
        bounds = WorldBounds(
            min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys),
        )
        return cls(
            title=title,
            drone_count=flyin_map.drone_count,
            zones=zones,
            connections=connections,
            bounds=bounds,
        )

    def zone(self, name: str) -> VisualZone:
        """Return the zone with the given name.

        Raises:
            KeyError: If no zone has that name.
        """
        for zone in self.zones:
            if zone.name == name:
                return zone
        raise KeyError(name)

    def zone_type_counts(self) -> dict[ZoneType, int]:
        """Return how many zones the map has of each zone type."""
        counts = {zone_type: 0 for zone_type in ZoneType}
        for zone in self.zones:
            counts[zone.zone_type] += 1
        return counts


def _visual_zone(zone: Zone, flyin_map: FlyInMap) -> VisualZone:
    """Convert one domain zone into its display model."""
    if zone.name == flyin_map.start:
        role = ZoneRole.START
    elif zone.name == flyin_map.goal:
        role = ZoneRole.END
    else:
        role = ZoneRole.HUB

    # The parser stores max_drones=1 for start/end, but the subject gives
    # them unlimited capacity; show that rule instead of the raw field.
    max_drones = None if role is not ZoneRole.HUB else zone.max_drones

    return VisualZone(
        name=zone.name,
        world_x=zone.x,
        world_y=zone.y,
        zone_type=zone.zone_type,
        role=role,
        max_drones=max_drones,
        color=zone.color,
    )
