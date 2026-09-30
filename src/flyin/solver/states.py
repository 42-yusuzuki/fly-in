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
    """A drone in transit across a connection at a particular turn.

    This node models the single intermediate turn of a 2-turn
    transit into a restricted zone: a drone that leaves its origin
    zone becomes "airborne" on the connection for one turn before
    landing at ``destination`` on the following turn. ``destination``
    is part of the identity of the state so that the two directions
    of the same connection never share a node, even when both
    endpoints are restricted and the transit happens on the same
    turn.
    """

    connection_id: int
    turn: int
    destination: str
