"""Textual application shell for the terminal visualizer.

This module only wires widgets, layout, and key bindings together. All
geometry and drawing lives in Textual-free modules (``viewport``,
``canvas``, ``renderer``).
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.events import Resize
from textual.widgets import Footer, Static

from flyin.domain.map import FlyInMap
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.widgets.graph_view import GraphView
from flyin.visualization.tui.widgets.status_panel import StatusPanel

MIN_COLUMNS = 100
MIN_ROWS = 30


class FlyInVisualizerApp(App[None]):
    """Static terminal graph viewer for one Fly-in map (Milestone 1)."""

    TITLE = "Fly-in"
    CSS = """
    Screen {
        background: #0b1120;
        color: #cbd5e1;
    }
    #title-bar {
        height: 1;
        padding: 0 1;
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
    }
    #main {
        height: 1fr;
    }
    #graph {
        width: 1fr;
        border: round #334155;
    }
    #status {
        width: 34;
        padding: 0 1;
        border: round #334155;
    }
    #too-small {
        display: none;
        height: 1fr;
        content-align: center middle;
        color: #f43f5e;
    }
    .cramped #main {
        display: none;
    }
    .cramped #too-small {
        display: block;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, visual_map: VisualMap) -> None:
        """Create the app for an already-built presentation model.

        Args:
            visual_map: Map to display.
        """
        super().__init__()
        self._visual_map = visual_map

    def compose(self) -> ComposeResult:
        """Lay out the title bar, graph, status panel, and footer."""
        yield Static(f"Fly-in  {self._visual_map.title}", id="title-bar")
        with Horizontal(id="main"):
            yield GraphView(self._visual_map, widget_id="graph")
            yield StatusPanel(self._visual_map, widget_id="status")
        yield Static("", id="too-small")
        yield Footer()

    def on_mount(self) -> None:
        """Apply the minimum-size check for the initial terminal size."""
        self._update_size_guard(self.size.width, self.size.height)

    def on_resize(self, event: Resize) -> None:
        """Re-check the minimum terminal size whenever it changes."""
        self._update_size_guard(event.size.width, event.size.height)

    def _update_size_guard(self, columns: int, rows: int) -> None:
        """Hide the graph behind a notice when the terminal is too small."""
        cramped = columns < MIN_COLUMNS or rows < MIN_ROWS
        self.screen.set_class(cramped, "cramped")
        if cramped:
            self.query_one("#too-small", Static).update(
                f"Terminal too small: {columns}x{rows}\n"
                f"Need at least {MIN_COLUMNS}x{MIN_ROWS}. Resize or press q."
            )


def run_visualizer(flyin_map: FlyInMap, title: str) -> None:
    """Open the terminal graph viewer for a parsed map and block until quit.

    Args:
        flyin_map: Parsed map to display. It is only read.
        title: Short name shown in the title bar (e.g. the file name).
    """
    FlyInVisualizerApp(VisualMap.from_flyin_map(flyin_map, title)).run()
