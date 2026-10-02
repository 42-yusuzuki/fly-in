"""Zone domain models."""

from dataclasses import dataclass
from enum import Enum


class ZoneType(Enum):
    """Fly-in zone type."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Zone:
    """A zone in the Fly-in map."""

    name: str
    x: int
    y: int
    zone_type: ZoneType
    max_drones: int
    color: str | None = None
