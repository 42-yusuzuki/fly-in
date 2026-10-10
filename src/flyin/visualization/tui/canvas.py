"""Character-cell canvas and raster helpers.

The canvas is plain Python: it stores one character and one optional
style string per cell. Style strings are interpreted by whichever
backend draws the canvas (Rich/Textual today), so nothing here depends
on a UI library.
"""

from dataclasses import dataclass

_BLANK = " "


@dataclass(frozen=True)
class Cell:
    """One terminal cell: a single character and an optional style."""

    char: str = _BLANK
    style: str | None = None


class CellCanvas:
    """Fixed-size grid of cells with simple drawing primitives.

    Writes outside the canvas are silently ignored, so callers can draw
    shapes that are partially off-screen without bounds checks.
    """

    def __init__(self, width: int, height: int) -> None:
        """Create a blank canvas.

        Args:
            width: Number of columns (negative values become 0).
            height: Number of rows (negative values become 0).
        """
        self._width = max(width, 0)
        self._height = max(height, 0)
        self._cells: list[list[Cell]] = []
        self.clear()

    @property
    def width(self) -> int:
        """Return the canvas width in columns."""
        return self._width

    @property
    def height(self) -> int:
        """Return the canvas height in rows."""
        return self._height

    def clear(self) -> None:
        """Reset every cell to a blank, unstyled space."""
        blank = Cell()
        self._cells = [
            [blank] * self._width for _ in range(self._height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        """Return whether ``(x, y)`` is a cell of this canvas."""
        return 0 <= x < self._width and 0 <= y < self._height

    def get(self, x: int, y: int) -> Cell:
        """Return the cell at ``(x, y)``.

        Raises:
            IndexError: If the position is outside the canvas.
        """
        if not self.in_bounds(x, y):
            raise IndexError(f"cell ({x}, {y}) is outside the canvas")
        return self._cells[y][x]

    def put(self, x: int, y: int, char: str, style: str | None = None) -> None:
        """Write a single character at ``(x, y)`` if it is on the canvas."""
        if len(char) != 1:
            raise ValueError(f"expected a single character, got {char!r}")
        if self.in_bounds(x, y):
            self._cells[y][x] = Cell(char, style)

    def text(self, x: int, y: int, text: str, style: str | None = None) -> None:
        """Write ``text`` left-to-right starting at ``(x, y)``, clipped."""
        for offset, char in enumerate(text):
            self.put(x + offset, y, char, style)

    def line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        style: str | None = None,
    ) -> None:
        """Draw a straight line between two cells, endpoints included."""
        points = raster_line(x1, y1, x2, y2)
        for index, (x, y) in enumerate(points):
            if index > 0:
                prev_x, prev_y = points[index - 1]
                char = line_char(x - prev_x, y - prev_y)
            elif len(points) > 1:
                next_x, next_y = points[1]
                char = line_char(next_x - x, next_y - y)
            else:
                char = line_char(0, 0)
            self.put(x, y, char, style)

    def rows(self) -> list[list[Cell]]:
        """Return a copy of the grid, row by row."""
        return [list(row) for row in self._cells]

    def plain_lines(self) -> list[str]:
        """Return the canvas characters without styles, one string per row."""
        return ["".join(cell.char for cell in row) for row in self._cells]


def raster_line(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    """Return the cells of a line from ``(x1, y1)`` to ``(x2, y2)``.

    Uses Bresenham's algorithm; both endpoints are included and the
    cells are ordered from the first endpoint to the second.
    """
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    step_x = 1 if x1 < x2 else -1
    step_y = 1 if y1 < y2 else -1
    error = dx + dy

    points: list[tuple[int, int]] = []
    x, y = x1, y1
    while True:
        points.append((x, y))
        if x == x2 and y == y2:
            return points
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x += step_x
        if doubled <= dx:
            error += dx
            y += step_y


def line_char(step_x: int, step_y: int) -> str:
    """Return the box-drawing character for one raster step.

    Screen rows grow downward, so a step of ``(+1, +1)`` goes down-right.
    """
    if step_x == 0 and step_y == 0:
        return "·"
    if step_y == 0:
        return "─"
    if step_x == 0:
        return "│"
    if (step_x > 0) == (step_y > 0):
        return "╲"
    return "╱"
