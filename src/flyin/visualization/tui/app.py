"""Textual application shell for the terminal visualizer.

This module only wires widgets, layout, and key bindings together. All
geometry, drawing, and playback state live in Textual-free modules
(``viewport``, ``canvas``, ``renderer``, ``animation``).
"""

import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.timer import Timer
from textual.widgets import Footer, Static

from flyin.domain.map import FlyInMap
from flyin.simulation.simulation import Simulation
from flyin.visualization.tui.animation import PlaybackController
from flyin.visualization.tui.inspection import Selectable, selectables
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots
from flyin.visualization.tui.widgets.graph_view import GraphView
from flyin.visualization.tui.widgets.help import HelpScreen
from flyin.visualization.tui.widgets.inspector import Inspector
from flyin.visualization.tui.widgets.status_panel import StatusPanel
from flyin.visualization.tui.widgets.timeline import Timeline

MIN_COLUMNS = 100
MIN_ROWS = 30
#: Animation frames per second while playing.
FPS = 30


class FlyInVisualizerApp(App[None]):
    """Terminal viewer that plays back or steps through a solved simulation."""

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
    #side {
        width: 34;
    }
    #inspector, #status {
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    #inspector {
        height: auto;
        max-height: 60%;
        padding: 0 1;
        border: round #f8fafc;
    }
    #status {
        height: 1fr;
        padding: 0 1;
        border: round #334155;
    }
    #timeline {
        height: 2;
        padding: 0 1;
    }
    #too-small {
        display: none;
        height: 1fr;
        content-align: center middle;
        color: #f43f5e;
    }
    .cramped #main, .cramped #timeline {
        display: none;
    }
    .cramped #too-small {
        display: block;
    }
    """
    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("left", "previous_turn", "Prev turn"),
        Binding("right", "next_turn", "Next turn"),
        Binding("home", "first_turn", "First", show=False),
        Binding("end", "last_turn", "Last", show=False),
        Binding("plus", "faster", "Faster", show=False),
        Binding("equals_sign", "faster", "Faster", show=False),
        Binding("minus", "slower", "Slower", show=False),
        Binding("r", "restart", "Restart", show=False),
        # Priority bindings override the screen's Tab focus navigation;
        # nothing in this app takes keyboard focus.
        Binding("tab", "select_next", "Select", priority=True),
        Binding("shift+tab", "select_previous", "Select back", show=False,
                priority=True),
        Binding("escape", "clear_selection", "Clear", show=False),
        Binding("question_mark", "show_help", "Help"),
        Binding("q", "quit", "Quit"),
    ]
    #: Actions still allowed while the help overlay is open.
    _HELP_ACTIONS = frozenset({"quit"})

    def __init__(
        self,
        visual_map: VisualMap,
        snapshots: tuple[TurnSnapshot, ...],
        frame_rate: float = FPS,
    ) -> None:
        """Create the app for an already-built presentation model.

        Args:
            visual_map: Map to display.
            snapshots: One snapshot per turn, starting at turn 0.
            frame_rate: Animation frames per second while playing.

        Raises:
            ValueError: If ``snapshots`` is empty or ``frame_rate`` is
                not positive.
        """
        if not snapshots:
            raise ValueError("need at least the turn-0 snapshot")
        if frame_rate <= 0:
            raise ValueError("frame_rate must be positive")
        super().__init__()
        self._frame_rate = frame_rate
        self._visual_map = visual_map
        self._snapshots = snapshots
        self._playback = PlaybackController(len(snapshots) - 1)
        self._selectables = selectables(visual_map)
        self._selection_index: int | None = None
        self._frame_timer: Timer | None = None
        self._last_frame = 0.0

    @property
    def playback(self) -> PlaybackController:
        """Return the playback state (turn, progress, speed, playing)."""
        return self._playback

    @property
    def selected(self) -> Selectable | None:
        """Return the zone or connection being inspected, if any."""
        if self._selection_index is None:
            return None
        return self._selectables[self._selection_index]

    @property
    def turn(self) -> int:
        """Return the turn currently displayed."""
        return self._playback.turn

    @property
    def last_turn(self) -> int:
        """Return the final turn of the simulation."""
        return self._playback.last_turn

    def compose(self) -> ComposeResult:
        """Lay out the title bar, graph, status panel, and footer."""
        snapshot = self._snapshots[self.turn]
        yield Static(self._title_text(), id="title-bar")
        with Horizontal(id="main"):
            yield GraphView(self._visual_map, snapshot, widget_id="graph")
            with Vertical(id="side"):
                yield Inspector(self._visual_map, widget_id="inspector")
                yield StatusPanel(
                    self._visual_map, snapshot, self.last_turn,
                    widget_id="status",
                )
        yield Timeline(self.last_turn, widget_id="timeline")
        yield Static("", id="too-small")
        yield Footer()

    def action_toggle_play(self) -> None:
        """Play or pause; playing from the last turn starts over."""
        self._playback.toggle()
        if self._playback.playing:
            self._last_frame = time.monotonic()
            self._timer().resume()
        else:
            self._timer().pause()
        self._refresh_view()

    def action_next_turn(self) -> None:
        """Show the next turn at rest, stopping at the last one."""
        self._playback.step(1)
        self._refresh_view()

    def action_previous_turn(self) -> None:
        """Show the previous turn at rest, stopping at turn 0."""
        self._playback.step(-1)
        self._refresh_view()

    def action_first_turn(self) -> None:
        """Jump to turn 0."""
        self._playback.go_to(0)
        self._refresh_view()

    def action_last_turn(self) -> None:
        """Jump to the final turn."""
        self._playback.go_to(self.last_turn)
        self._refresh_view()

    def action_faster(self) -> None:
        """Increase playback speed."""
        self._playback.faster()
        self._refresh_view()

    def action_slower(self) -> None:
        """Decrease playback speed."""
        self._playback.slower()
        self._refresh_view()

    def action_restart(self) -> None:
        """Return to turn 0 and pause."""
        self._playback.restart()
        self._timer().pause()
        self._refresh_view()

    def action_select_next(self) -> None:
        """Inspect the next zone or connection (zones first)."""
        self._cycle_selection(1)

    def action_select_previous(self) -> None:
        """Inspect the previous zone or connection."""
        self._cycle_selection(-1)

    def action_clear_selection(self) -> None:
        """Stop inspecting and hide the inspector."""
        self._selection_index = None
        self._refresh_view()

    def _cycle_selection(self, delta: int) -> None:
        if not self._selectables:
            return
        if self._selection_index is None:
            start = 0 if delta > 0 else len(self._selectables) - 1
            self._selection_index = start
        else:
            self._selection_index = (
                (self._selection_index + delta) % len(self._selectables)
            )
        self._refresh_view()

    def action_show_help(self) -> None:
        """Open the help overlay."""
        self.push_screen(HelpScreen())

    def check_action(
        self, action: str, parameters: tuple[object, ...],
    ) -> bool | None:
        """Disable the viewer's own keys while the help overlay is open."""
        if isinstance(self.screen, HelpScreen):
            return action in self._HELP_ACTIONS
        return True

    def on_graph_view_picked(self, message: GraphView.Picked) -> None:
        """Inspect whatever was clicked; clicking empty space clears."""
        selected = message.selected
        self._selection_index = (
            None if selected is None else self._selectables.index(selected)
        )
        self._refresh_view()

    def on_timeline_seek(self, message: Timeline.Seek) -> None:
        """Jump to the clicked turn, at rest."""
        self._playback.go_to(message.turn)
        self._refresh_view()

    def advance(self, elapsed: float) -> None:
        """Advance playback by ``elapsed`` seconds and redraw.

        Called by the frame timer; tests call it directly to drive
        playback deterministically.
        """
        turn_before = self.turn
        self._playback.tick(elapsed)
        if not self._playback.playing:
            self._timer().pause()
        self._refresh_view(
            graph_only=self.turn == turn_before and self._playback.playing,
        )

    def _on_frame(self) -> None:
        now = time.monotonic()
        elapsed, self._last_frame = now - self._last_frame, now
        self.advance(elapsed)

    def _timer(self) -> Timer:
        if self._frame_timer is None:
            self._frame_timer = self.set_interval(
                1 / self._frame_rate, self._on_frame, pause=True,
            )
        return self._frame_timer

    def _refresh_view(self, graph_only: bool = False) -> None:
        """Redraw the graph, and unless ``graph_only`` the text panels."""
        playback = self._playback
        snapshot = self._snapshots[playback.turn]
        previous = self._snapshots[playback.turn - 1] if playback.turn else None
        self.query_one(GraphView).show(
            snapshot, previous, playback.progress, self.selected,
        )
        self.query_one(Timeline).show(playback.turn - 1 + playback.progress)
        if graph_only:
            return
        self.query_one(Inspector).show(snapshot, self.selected)
        self.query_one(StatusPanel).show(snapshot, playback.label)
        self.query_one("#title-bar", Static).update(self._title_text())

    def _title_text(self) -> str:
        return (
            f"Fly-in  {self._visual_map.title}"
            f"    Turn {self.turn} / {self.last_turn}"
            f"    {self._playback.label}"
        )

    def on_mount(self) -> None:
        """Show the initial frame and check the initial terminal size."""
        self._refresh_view()
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
