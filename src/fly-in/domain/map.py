"""Fly-in map domain model."""

from dataclasses import dataclass

from flyin.domain.connection import Connection
from flyin.domain.zone import Zone


@dataclass(frozen=True)
class FlyInMap:
    """Complete parsed Fly-in map."""

    drone_count: int
    start: str
    goal: str
    zones: dict[str, Zone]
    connections: list[Connection]
