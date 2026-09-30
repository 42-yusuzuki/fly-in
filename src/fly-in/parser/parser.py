"""Fly-in map parser."""

from pathlib import Path

from flyin.domain.map import FlyInMap


class FlyInParser:
    """Parse Fly-in input files."""

    def parse(self, path: Path) -> FlyInMap:
        """Parse a map file.

        Args:
            path: Input map path.

        Returns:
            Parsed FlyInMap.
        """
        raise NotImplementedError
