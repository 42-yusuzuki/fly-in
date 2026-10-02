"""Fly-in map parser."""

import re
from pathlib import Path

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.parser.errors import FlyInParseError

_ZONE_PREFIXES = ("start_hub:", "end_hub:", "hub:")
_NB_DRONES_RE = re.compile(r"^nb_drones:\s*(\S+)$")
_ZONE_BODY_RE = re.compile(
    r"^(?P<name>[^\s\-\[\]]+)\s+(?P<x>-?\d+)\s+(?P<y>-?\d+)"
    r"\s*(\[(?P<meta>.*)\])?$"
)
_CONNECTION_RE = re.compile(
    r"^connection:\s*(?P<source>[^\s\-\[\]]+)-(?P<destination>[^\s\-\[\]]+)"
    r"\s*(\[(?P<meta>.*)\])?$"
)
_ZONE_TYPES_BY_VALUE = {zone_type.value: zone_type for zone_type in ZoneType}


class FlyInParser:
    """Parse Fly-in input files."""

    def parse(self, path: Path) -> FlyInMap:
        """Parse a map file.

        Args:
            path: Input map path.

        Returns:
            Parsed FlyInMap.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise FlyInParseError(f"cannot read map file '{path}': {exc}") from exc

        drone_count: int | None = None
        start: str | None = None
        goal: str | None = None
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
        seen_pairs: set[frozenset[str]] = set()
        next_connection_id = 1

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = self._strip_comment(raw_line).strip()
            if not line:
                continue

            if drone_count is None:
                drone_count = self._parse_nb_drones(line, line_number)
                continue

            if line.startswith("connection:"):
                connection = self._parse_connection(
                    line, line_number, zones, next_connection_id,
                )
                pair = frozenset((connection.source, connection.destination))
                if pair in seen_pairs:
                    raise FlyInParseError(
                        f"line {line_number}: duplicate connection "
                        f"'{connection.source}-{connection.destination}'"
                    )
                seen_pairs.add(pair)
                connections.append(connection)
                next_connection_id += 1
                continue

            zone, role = self._parse_zone(line, line_number)
            if zone.name in zones:
                raise FlyInParseError(
                    f"line {line_number}: duplicate zone name '{zone.name}'"
                )
            zones[zone.name] = zone

            if role == "start_hub":
                if start is not None:
                    raise FlyInParseError(
                        f"line {line_number}: multiple start_hub zones defined"
                    )
                start = zone.name
            elif role == "end_hub":
                if goal is not None:
                    raise FlyInParseError(
                        f"line {line_number}: multiple end_hub zones defined"
                    )
                goal = zone.name

        if drone_count is None:
            raise FlyInParseError("missing 'nb_drones' declaration")
        if start is None:
            raise FlyInParseError("missing 'start_hub' zone")
        if goal is None:
            raise FlyInParseError("missing 'end_hub' zone")

        return FlyInMap(
            drone_count=drone_count,
            start=start,
            goal=goal,
            zones=zones,
            connections=connections,
        )

    def _strip_comment(self, raw_line: str) -> str:
        """Strip everything from the first '#' onward."""
        index = raw_line.find("#")
        if index == -1:
            return raw_line
        return raw_line[:index]

    def _parse_nb_drones(self, line: str, line_number: int) -> int:
        """Parse the mandatory leading 'nb_drones: <positive_integer>' line."""
        match = _NB_DRONES_RE.match(line)
        if not match:
            raise FlyInParseError(
                f"line {line_number}: expected 'nb_drones: <positive_integer>' "
                "as the first declaration"
            )
        return self._parse_positive_int(match.group(1), line_number, "nb_drones")

    def _parse_positive_int(self, token: str, line_number: int, field: str) -> int:
        """Parse a token as a strictly positive integer."""
        try:
            value = int(token)
        except ValueError as exc:
            raise FlyInParseError(
                f"line {line_number}: '{field}' must be a positive integer, "
                f"got '{token}'"
            ) from exc
        if value <= 0:
            raise FlyInParseError(
                f"line {line_number}: '{field}' must be a positive integer, "
                f"got '{token}'"
            )
        return value

    def _parse_metadata(self, meta_str: str, line_number: int) -> dict[str, str]:
        """Parse a space-separated 'key=value' metadata block."""
        metadata: dict[str, str] = {}
        for token in meta_str.split():
            key, separator, value = token.partition("=")
            if not separator or not key or not value:
                raise FlyInParseError(
                    f"line {line_number}: invalid metadata token '{token}'"
                )
            metadata[key] = value
        return metadata

    def _parse_zone_type(self, value: str, line_number: int) -> ZoneType:
        """Parse a 'zone=<type>' metadata value."""
        zone_type = _ZONE_TYPES_BY_VALUE.get(value)
        if zone_type is None:
            raise FlyInParseError(
                f"line {line_number}: invalid zone type '{value}', expected one "
                "of normal, blocked, restricted, priority"
            )
        return zone_type

    def _parse_zone(self, line: str, line_number: int) -> tuple[Zone, str]:
        """Parse a 'start_hub:'/'end_hub:'/'hub:' zone declaration."""
        prefix = next((p for p in _ZONE_PREFIXES if line.startswith(p)), None)
        if prefix is None:
            raise FlyInParseError(
                f"line {line_number}: expected a zone or connection "
                f"declaration, got '{line}'"
            )
        role = prefix[:-1]
        rest = line[len(prefix):].strip()

        match = _ZONE_BODY_RE.match(rest)
        if not match:
            raise FlyInParseError(
                f"line {line_number}: invalid zone declaration '{line}'"
            )

        name = match.group("name")
        metadata = self._parse_metadata(match.group("meta") or "", line_number)

        zone_type = self._parse_zone_type(
            metadata.get("zone", ZoneType.NORMAL.value), line_number,
        )

        max_drones = 1
        if role == "hub" and "max_drones" in metadata:
            max_drones = self._parse_positive_int(
                metadata["max_drones"], line_number, "max_drones",
            )

        zone = Zone(
            name=name,
            x=int(match.group("x")),
            y=int(match.group("y")),
            zone_type=zone_type,
            max_drones=max_drones,
            color=metadata.get("color"),
        )
        return zone, role

    def _parse_connection(
        self,
        line: str,
        line_number: int,
        zones: dict[str, Zone],
        connection_id: int,
    ) -> Connection:
        """Parse a 'connection: <name1>-<name2> [metadata]' declaration."""
        match = _CONNECTION_RE.match(line)
        if not match:
            raise FlyInParseError(
                f"line {line_number}: invalid connection declaration '{line}'"
            )

        source = match.group("source")
        destination = match.group("destination")

        for name in (source, destination):
            if name not in zones:
                raise FlyInParseError(
                    f"line {line_number}: connection references undefined "
                    f"zone '{name}'"
                )
        if source == destination:
            raise FlyInParseError(
                f"line {line_number}: connection cannot link a zone to itself "
                f"('{source}')"
            )

        metadata = self._parse_metadata(match.group("meta") or "", line_number)
        max_capacity = 1
        if "max_link_capacity" in metadata:
            max_capacity = self._parse_positive_int(
                metadata["max_link_capacity"], line_number, "max_link_capacity",
            )

        return Connection(
            connection_id=connection_id,
            source=source,
            destination=destination,
            max_capacity=max_capacity,
        )
