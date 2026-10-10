"""Headless tests for the Textual visualizer shell."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Static

from flyin.parser.parser import FlyInParser
from flyin.simulation.simulation import Simulation
from flyin.solver.solver import FlyInSolver
from flyin.visualization.tui.animation import TURN_DURATION
from flyin.visualization.tui.app import FlyInVisualizerApp
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots
from flyin.visualization.tui.widgets.graph_view import GraphView, canvas_to_text
from flyin.visualization.tui.renderer import GraphRenderer
from flyin.visualization.tui.widgets.help import HelpScreen, build_help_text
from flyin.visualization.tui.widgets.inspector import Inspector
from flyin.visualization.tui.widgets.timeline import Timeline
from flyin.visualization.tui.widgets.status_panel import (
    MAX_LISTED_MOVES,
    StatusPanel,
    build_status_text,
)
from flyin.visualization.tui.canvas import CellCanvas

_MAP = Path(__file__).parent.parent / "maps" / "subject-example.flyin"


def _visual_map() -> VisualMap:
    return VisualMap.from_flyin_map(FlyInParser().parse(_MAP), _MAP.name)


def _snapshots() -> tuple[TurnSnapshot, ...]:
    flyin_map = FlyInParser().parse(_MAP)
    simulation = Simulation(paths=FlyInSolver().solve(flyin_map).paths)
    return build_snapshots(simulation, flyin_map.goal)


def _app() -> FlyInVisualizerApp:
    return FlyInVisualizerApp(_visual_map(), _snapshots())


def test_app_renders_graph_and_quits() -> None:
    async def scenario() -> None:
        app = _app()
        async with app.run_test(size=(120, 40)) as pilot:
            assert not app.screen.has_class("cramped")
            graph = app.query_one(GraphView)
            assert graph.content_size.width > 0
            rendered = graph.render().plain
            assert "◉" in rendered and "◎" in rendered
            assert "D×5" in rendered
            await pilot.press("q")
        assert app.return_code == 0

    asyncio.run(scenario())


def test_app_shows_notice_when_terminal_too_small() -> None:
    async def scenario() -> None:
        app = _app()
        async with app.run_test(size=(60, 20)):
            assert app.screen.has_class("cramped")

    asyncio.run(scenario())


def test_arrow_keys_step_through_turns() -> None:
    async def scenario() -> None:
        app = _app()
        last = app.last_turn
        async with app.run_test(size=(120, 40)) as pilot:
            graph = app.query_one(GraphView)
            title = app.query_one("#title-bar", Static)
            await pilot.press("left")
            assert app.turn == 0

            await pilot.press("right", "right")
            assert app.turn == 2
            assert f"Turn 2 / {last}" in str(title.render())
            assert "D×5" not in graph.render().plain

            await pilot.press("end", "right")
            assert app.turn == last
            await pilot.press("left")
            assert app.turn == last - 1
            await pilot.press("home")
            assert app.turn == 0
            panel = app.query_one(StatusPanel)
            assert f"Turn         0 / {last}" in str(panel.render())

    asyncio.run(scenario())


def test_space_plays_until_the_end_and_restart_pauses() -> None:
    async def scenario() -> None:
        # A near-zero frame rate keeps the real clock out of the way, so
        # playback only moves when the test calls advance().
        app = FlyInVisualizerApp(_visual_map(), _snapshots(), frame_rate=1e-6)
        last = app.last_turn
        async with app.run_test(size=(120, 40)) as pilot:
            title = app.query_one("#title-bar", Static)
            await pilot.press("space")
            assert app.playback.playing
            assert "Playing 1x" in str(title.render())

            app.advance(TURN_DURATION * 1.5)
            assert app.turn == 2
            assert app.playback.progress == pytest.approx(0.5)

            await pilot.press("space")
            app.advance(TURN_DURATION * 10)
            assert app.turn == 2
            assert "Paused 1x" in str(title.render())

            await pilot.press("plus", "plus", "minus")
            assert app.playback.speed == 2.0

            await pilot.press("space")
            app.advance(TURN_DURATION * 100)
            assert app.turn == last and not app.playback.playing

            await pilot.press("r")
            assert (app.turn, app.playback.playing) == (0, False)

    asyncio.run(scenario())


def test_tab_cycles_selection_and_escape_clears_it() -> None:
    async def scenario() -> None:
        app = _app()
        visual = _visual_map()
        async with app.run_test(size=(120, 40)) as pilot:
            inspector = app.query_one(Inspector)
            assert app.selected is None and not inspector.display

            await pilot.press("tab")
            assert app.selected == visual.zones[0]
            assert inspector.display
            assert f"Zone         {visual.zones[0].name}" in str(inspector.render())

            await pilot.press("shift+tab")
            assert app.selected == visual.connections[-1]
            assert "Connection" in str(inspector.render())

            await pilot.press("right")
            assert "(turn 1)" in str(inspector.render())

            await pilot.press("escape")
            assert app.selected is None and not inspector.display

    asyncio.run(scenario())


def test_clicking_graph_selects_and_empty_space_clears() -> None:
    async def scenario() -> None:
        app = _app()
        visual = _visual_map()
        async with app.run_test(size=(120, 40)) as pilot:
            graph = app.query_one(GraphView)
            size = graph.content_size
            renderer = GraphRenderer(visual)
            x, y = renderer.layout(size.width, size.height)["roof1"]
            # The graph has a 1-cell border around its content.
            await pilot.click(GraphView, offset=(x + 1, y + 1))
            assert app.selected == visual.zone("roof1")

            await pilot.click(GraphView, offset=(size.width, 1))
            assert app.selected is None

    asyncio.run(scenario())


def test_clicking_timeline_seeks() -> None:
    async def scenario() -> None:
        app = _app()
        async with app.run_test(size=(120, 40)) as pilot:
            timeline = app.query_one(Timeline)
            width = timeline.content_size.width
            # The timeline has 1 column of padding on the left.
            await pilot.click(Timeline, offset=(width, 0))
            assert app.turn == app.last_turn
            await pilot.click(Timeline, offset=(1, 0))
            assert app.turn == 0

    asyncio.run(scenario())


def test_help_overlay_blocks_viewer_keys_until_closed() -> None:
    async def scenario() -> None:
        app = _app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpScreen)
            help_text = app.screen.query_one("#help-text", Static)
            assert help_text.size.width >= 40 and help_text.size.height >= 10

            await pilot.press("right", "tab", "space")
            assert app.turn == 0
            assert app.selected is None
            assert not app.playback.playing

            await pilot.press("escape")
            assert not isinstance(app.screen, HelpScreen)
            await pilot.press("question_mark", "question_mark")
            assert not isinstance(app.screen, HelpScreen)

            await pilot.press("right")
            assert app.turn == 1

    asyncio.run(scenario())


def test_help_text_lists_every_bound_key() -> None:
    text = build_help_text().plain

    for keys in ("Space", "Tab / Shift+Tab", "Click timeline", "Esc", "?"):
        assert keys in text


def test_status_text_lists_turn_counts_and_map_metadata() -> None:
    visual = _visual_map()
    snapshots = _snapshots()
    text = build_status_text(visual, snapshots[0], len(snapshots) - 1).plain

    assert _MAP.name in text
    assert f"Drones       {visual.drone_count}" in text
    assert f"Zones        {len(visual.zones)}" in text
    assert f"  Waiting    {visual.drone_count}" in text
    assert "  Delivered  0" in text
    assert "(none)" in text


def test_status_text_lists_moves_and_truncates() -> None:
    visual = _visual_map()
    snapshots = _snapshots()
    moving = next(s for s in snapshots if s.movers())
    text = build_status_text(visual, moving, len(snapshots) - 1).plain

    mover = moving.movers()[0]
    assert f"{mover.source} " in text and f" {mover.target}" in text

    crowded = TurnSnapshot(
        turn=moving.turn, drones=moving.movers() * (MAX_LISTED_MOVES + 1),
    )
    text = build_status_text(visual, crowded, len(snapshots) - 1).plain
    hidden = len(crowded.movers()) - MAX_LISTED_MOVES
    assert f"+{hidden} more" in text


def test_app_rejects_empty_snapshots() -> None:
    with pytest.raises(ValueError):
        FlyInVisualizerApp(_visual_map(), ())


def test_canvas_to_text_merges_style_runs() -> None:
    canvas = CellCanvas(4, 2)
    canvas.text(0, 0, "ab", "red")
    canvas.text(2, 0, "cd", "blue")

    text = canvas_to_text(canvas)

    assert text.plain == "abcd\n    "
    assert [span.style for span in text.spans] == ["red", "blue"]
