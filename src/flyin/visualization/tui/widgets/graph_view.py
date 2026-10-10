"""Main graph area of the terminal visualizer."""

from rich.text import Text
from textual.widget import Widget

from flyin.visualization.tui.canvas import CellCanvas
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.renderer import GraphRenderer


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
    """Draw the static map topology, sized to the widget.

    The rendered text is cached per widget size, so the graph is only
    re-rasterized when the terminal is resized.
    """

    def __init__(self, visual_map: VisualMap, widget_id: str | None = None) -> None:
        """Create the view.

        Args:
            visual_map: Map to display.
            widget_id: Optional Textual widget id.
        """
        super().__init__(id=widget_id)
        self._renderer = GraphRenderer(visual_map)
        self._cache: tuple[tuple[int, int], Text] | None = None

    def render(self) -> Text:
        """Return the graph rendered for the current content size."""
        size = (self.content_size.width, self.content_size.height)
        if self._cache is None or self._cache[0] != size:
            canvas = self._renderer.render(*size)
            self._cache = (size, canvas_to_text(canvas))
        return self._cache[1]
