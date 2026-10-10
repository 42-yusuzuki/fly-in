"""Headless tests for the Textual visualizer shell."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Static

from flyin.parser.parser import FlyInParser
from flyin.simulation.simulation import Simulation
from flyin.solver.solver import FlyInSolver
from flyin.visualization.tui.app import FlyInVisualizerApp
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots
from flyin.visualization.tui.widgets.graph_view import GraphView, canvas_to_text
from flyin.visualization.tui.widgets.status_panel import (
    MAX_LISTED_MOVES,
    StatusPanel,
    build_status_text,
    progress_bar,
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


def test_progress_bar() -> None:
    assert progress_bar(0, 4, width=4) == "[----]"
    assert progress_bar(2, 4, width=4) == "[==--]"
    assert progress_bar(4, 4, width=4) == "[====]"
    assert progress_bar(0, 0, width=4) == "[====]"


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
