"""Connection domain model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """A bidirectional connection between zones."""

    connection_id: int
    source: str
    destination: str
    max_capacity: int
