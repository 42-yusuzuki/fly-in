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
from flyin.simulation.simulation import Simulation
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots
from flyin.visualization.tui.widgets.graph_view import GraphView
from flyin.visualization.tui.widgets.status_panel import StatusPanel

MIN_COLUMNS = 100
MIN_ROWS = 30


class FlyInVisualizerApp(App[None]):
    """Terminal viewer stepping through a solved simulation turn by turn."""

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
    BINDINGS = [
        ("left", "previous_turn", "Prev turn"),
        ("right", "next_turn", "Next turn"),
        ("home", "first_turn", "First"),
        ("end", "last_turn", "Last"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self, visual_map: VisualMap, snapshots: tuple[TurnSnapshot, ...],
    ) -> None:
        """Create the app for an already-built presentation model.

        Args:
            visual_map: Map to display.
            snapshots: One snapshot per turn, starting at turn 0.

        Raises:
            ValueError: If ``snapshots`` is empty.
        """
        if not snapshots:
            raise ValueError("need at least the turn-0 snapshot")
        super().__init__()
        self._visual_map = visual_map
        self._snapshots = snapshots
        self._turn = 0

    @property
    def turn(self) -> int:
        """Return the turn currently displayed."""
        return self._turn

    @property
    def last_turn(self) -> int:
        """Return the final turn of the simulation."""
        return len(self._snapshots) - 1

    def compose(self) -> ComposeResult:
        """Lay out the title bar, graph, status panel, and footer."""
        snapshot = self._snapshots[self._turn]
        yield Static(self._title_text(), id="title-bar")
        with Horizontal(id="main"):
            yield GraphView(self._visual_map, snapshot, widget_id="graph")
            yield StatusPanel(
                self._visual_map, snapshot, self.last_turn, widget_id="status",
            )
        yield Static("", id="too-small")
        yield Footer()

    def action_next_turn(self) -> None:
        """Show the next turn, stopping at the last one."""
        self._go_to(self._turn + 1)

    def action_previous_turn(self) -> None:
        """Show the previous turn, stopping at turn 0."""
        self._go_to(self._turn - 1)

    def action_first_turn(self) -> None:
        """Jump to turn 0."""
        self._go_to(0)

    def action_last_turn(self) -> None:
        """Jump to the final turn."""
        self._go_to(self.last_turn)

    def _go_to(self, turn: int) -> None:
        """Display ``turn``, clamped to the simulated range."""
        turn = min(max(turn, 0), self.last_turn)
        if turn == self._turn:
            return
        self._turn = turn
        snapshot = self._snapshots[turn]
        self.query_one(GraphView).show(snapshot)
        self.query_one(StatusPanel).show(snapshot)
        self.query_one("#title-bar", Static).update(self._title_text())

    def _title_text(self) -> str:
        return (
            f"Fly-in  {self._visual_map.title}"
            f"    Turn {self._turn} / {self.last_turn}"
        )

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


def run_visualizer(
    flyin_map: FlyInMap, simulation: Simulation, title: str,
) -> None:
    """Open the terminal viewer for a solved map and block until quit.

    Args:
        flyin_map: Parsed map to display. It is only read.
        simulation: Solved simulation to step through. It is only read.
        title: Short name shown in the title bar (e.g. the file name).
    """
    FlyInVisualizerApp(
        VisualMap.from_flyin_map(flyin_map, title),
        build_snapshots(simulation, flyin_map.goal),
    ).run()
