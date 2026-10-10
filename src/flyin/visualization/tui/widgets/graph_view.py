"""Main graph area of the terminal visualizer."""

from rich.text import Text
from textual.widget import Widget

from flyin.visualization.tui.canvas import CellCanvas
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.renderer import GraphRenderer
from flyin.visualization.tui.snapshot import TurnSnapshot


def canvas_to_text(canvas: CellCanvas) -> Text:
    """Convert a canvas into a Rich ``Text``, merging same-style runs."""
    text = Text(no_wrap=True, overflow="crop")
    for row_index, row in enumerate(canvas.rows()):
        if row_index > 0:
            text.append("\n")
        run_chars: list[str] = []
        run_style: str | None = None
        for cell in row:
            if cell.style != run_style and run_chars:
                text.append("".join(run_chars), run_style)
                run_chars = []
            run_style = cell.style
            run_chars.append(cell.char)
        if run_chars:
            text.append("".join(run_chars), run_style)
    return text


class GraphView(Widget):
    """Draw the map and the drones of the selected turn, sized to the widget.

    The rendered text is cached per widget size and turn, so the graph
    is only re-rasterized on resize or when the turn changes.
    """

    def __init__(
        self,
        visual_map: VisualMap,
        snapshot: TurnSnapshot | None = None,
        widget_id: str | None = None,
    ) -> None:
        """Create the view.

        Args:
            visual_map: Map to display.
            snapshot: Turn whose drones are drawn, or ``None`` for the
                bare topology.
            widget_id: Optional Textual widget id.
        """
        super().__init__(id=widget_id)
        self._renderer = GraphRenderer(visual_map)
        self._snapshot = snapshot
        self._cache: tuple[tuple[int, int, int | None], Text] | None = None

    def show(self, snapshot: TurnSnapshot) -> None:
        """Switch to another turn and redraw."""
        self._snapshot = snapshot
        self.refresh()

    def render(self) -> Text:
        """Return the graph rendered for the current size and turn."""
        width, height = self.content_size.width, self.content_size.height
        turn = self._snapshot.turn if self._snapshot else None
        key = (width, height, turn)
        if self._cache is None or self._cache[0] != key:
            canvas = self._renderer.render(width, height, self._snapshot)
            self._cache = (key, canvas_to_text(canvas))
        return self._cache[1]
