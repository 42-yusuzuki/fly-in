"""Tests for the terminal visualizer's cell canvas and raster helpers."""

import pytest

from flyin.visualization.tui.canvas import CellCanvas, line_char, raster_line


def test_raster_line_horizontal() -> None:
    assert raster_line(0, 0, 3, 0) == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_raster_line_vertical_upward() -> None:
    assert raster_line(1, 3, 1, 0) == [(1, 3), (1, 2), (1, 1), (1, 0)]


def test_raster_line_diagonal() -> None:
    assert raster_line(0, 0, 2, 2) == [(0, 0), (1, 1), (2, 2)]


def test_raster_line_single_point() -> None:
    assert raster_line(4, 4, 4, 4) == [(4, 4)]


def test_raster_line_is_connected_and_reversible() -> None:
    forward = raster_line(0, 0, 7, 3)
    backward = raster_line(7, 3, 0, 0)

    assert forward[0] == (0, 0) and forward[-1] == (7, 3)
    assert backward[0] == (7, 3) and backward[-1] == (0, 0)
    for (ax, ay), (bx, by) in zip(forward, forward[1:]):
        assert max(abs(bx - ax), abs(by - ay)) == 1


@pytest.mark.parametrize(
    ("step", "expected"),
    [
        ((1, 0), "─"),
        ((-1, 0), "─"),
        ((0, 1), "│"),
        ((1, 1), "╲"),
        ((-1, -1), "╲"),
        ((1, -1), "╱"),
        ((-1, 1), "╱"),
    ],
)
def test_line_char(step: tuple[int, int], expected: str) -> None:
    assert line_char(*step) == expected


def test_canvas_line_drawing() -> None:
    canvas = CellCanvas(4, 3)
    canvas.line(0, 0, 3, 0, "edge")
    canvas.line(0, 2, 2, 0)

    assert canvas.plain_lines() == ["──╱─", " ╱  ", "╱   "]
    assert canvas.get(3, 0).style == "edge"


def test_canvas_ignores_out_of_bounds_writes() -> None:
    canvas = CellCanvas(3, 1)
    canvas.put(-1, 0, "x")
    canvas.put(3, 0, "x")
    canvas.text(1, 0, "abcdef")

    assert canvas.plain_lines() == [" ab"]


def test_canvas_put_rejects_multi_character_strings() -> None:
    with pytest.raises(ValueError):
        CellCanvas(2, 2).put(0, 0, "ab")


def test_canvas_clear_resets_cells() -> None:
    canvas = CellCanvas(2, 1)
    canvas.text(0, 0, "hi", "bold")
    canvas.clear()

    assert canvas.plain_lines() == ["  "]
    assert canvas.get(0, 0).style is None


def test_canvas_zero_size() -> None:
    canvas = CellCanvas(0, 0)
    canvas.line(0, 0, 5, 5)

    assert canvas.plain_lines() == []
