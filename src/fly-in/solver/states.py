"""States used by the time-expanded network."""

from dataclasses import dataclass
from enum import Enum


class NodeSide(Enum):
    """Side of a vertex-split zone."""

    IN = "in"
    OUT = "out"


@dataclass(frozen=True)
class ZoneState:
    """Zone state at a particular simulation turn."""

    zone_name: str
    turn: int
    side: NodeSide


@dataclass(frozen=True)
class ConnectionState:
    """Connection state at a particular simulation turn."""

    connection_id: int
    turn: int
