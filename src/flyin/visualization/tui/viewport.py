"""World-to-screen coordinate transform for the terminal graph view."""

import math
from dataclasses import dataclass

from flyin.visualization.tui.model import WorldBounds


@dataclass(frozen=True)
class Viewport:
    """Map integer world coordinates onto a grid of terminal cells.

    Each axis is normalized independently into the drawable area
    (the viewport minus its margins). The y axis is flipped so that
    larger map ``y`` values appear higher on screen. When every zone
    shares the same coordinate on an axis, zones are centered on that
    axis instead of dividing by zero.

    Attributes:
        bounds: World-space bounding box to fit.
        width: Viewport width in terminal columns.
        height: Viewport height in terminal rows.
        margin_x: Preferred blank columns on the left and right.
        margin_y: Preferred blank rows on the top and bottom.
    """

    bounds: WorldBounds
    width: int
    height: int
    margin_x: int = 2
    margin_y: int = 1

    def to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Return the unrounded screen position of a world coordinate."""
        left, drawable_width = _axis_extent(self.width, self.margin_x)
        top, drawable_height = _axis_extent(self.height, self.margin_y)

        normalized_x = _normalize(
            world_x - self.bounds.min_x, self.bounds.max_x - self.bounds.min_x,
        )
        normalized_y = _normalize(
            self.bounds.max_y - world_y, self.bounds.max_y - self.bounds.min_y,
        )
        return (
            left + normalized_x * drawable_width,
            top + normalized_y * drawable_height,
        )

    def to_cell(self, world_x: float, world_y: float) -> tuple[int, int]:
        """Return the terminal cell for a world coordinate.

        The position is rounded half-up and clamped to the viewport, so
        the result is always a valid cell even for out-of-bounds input.
        """
        screen_x, screen_y = self.to_screen(world_x, world_y)
        return (
            _clamp(_round_half_up(screen_x), 0, max(self.width - 1, 0)),
            _clamp(_round_half_up(screen_y), 0, max(self.height - 1, 0)),
        )


def _axis_extent(size: int, margin: int) -> tuple[int, int]:
    """Return ``(start, span)`` of the drawable range on one axis.

    The margin shrinks when the viewport is too small to honor it.
    """
    last = max(size - 1, 0)
    effective_margin = min(max(margin, 0), last // 2)
    return effective_margin, last - 2 * effective_margin


def _normalize(offset: float, span: int) -> float:
    """Return ``offset / span``, or the center (0.5) for a zero span."""
    if span == 0:
        return 0.5
    return offset / span


def _round_half_up(value: float) -> int:
    """Round to the nearest integer, ties going up (deterministic)."""
    return math.floor(value + 0.5)


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp an integer into ``[low, high]``."""
    return min(max(value, low), high)
