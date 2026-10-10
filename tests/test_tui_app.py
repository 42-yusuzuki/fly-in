"""Headless tests for the Textual visualizer shell."""

import asyncio
from pathlib import Path

from flyin.parser.parser import FlyInParser
from flyin.visualization.tui.app import FlyInVisualizerApp
from flyin.visualization.tui.model import VisualMap
from flyin.visualization.tui.widgets.graph_view import GraphView, canvas_to_text
from flyin.visualization.tui.widgets.status_panel import build_status_text
from flyin.visualization.tui.canvas import CellCanvas

_MAP = Path(__file__).parent.parent / "maps" / "subject-example.flyin"


def _visual_map() -> VisualMap:
    return VisualMap.from_flyin_map(FlyInParser().parse(_MAP), _MAP.name)


def test_app_renders_graph_and_quits() -> None:
    async def scenario() -> None:
        app = FlyInVisualizerApp(_visual_map())
        async with app.run_test(size=(120, 40)) as pilot:
            assert not app.screen.has_class("cramped")
            graph = app.query_one(GraphView)
            assert graph.content_size.width > 0
            rendered = graph.render().plain
            assert "◉" in rendered and "◎" in rendered
            await pilot.press("q")
        assert app.return_code == 0

    asyncio.run(scenario())


def test_app_shows_notice_when_terminal_too_small() -> None:
    async def scenario() -> None:
        app = FlyInVisualizerApp(_visual_map())
        async with app.run_test(size=(60, 20)):
            assert app.screen.has_class("cramped")

    asyncio.run(scenario())


def test_status_text_lists_map_metadata() -> None:
    visual = _visual_map()
    text = build_status_text(visual).plain

    assert _MAP.name in text
    assert f"Drones       {visual.drone_count}" in text
    assert f"Zones        {len(visual.zones)}" in text


def test_canvas_to_text_merges_style_runs() -> None:
    canvas = CellCanvas(4, 2)
    canvas.text(0, 0, "ab", "red")
    canvas.text(2, 0, "cd", "blue")

    text = canvas_to_text(canvas)

    assert text.plain == "abcd\n    "
    assert [span.style for span in text.spans] == ["red", "blue"]
