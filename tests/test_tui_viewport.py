"""Tests for the terminal visualizer's world-to-screen transform."""

from flyin.visualization.tui.model import WorldBounds
from flyin.visualization.tui.viewport import Viewport


def _viewport(
    bounds: WorldBounds, width: int = 21, height: int = 11,
) -> Viewport:
    return Viewport(bounds, width, height, margin_x=0, margin_y=0)


def test_min_and_max_corners_map_to_viewport_edges() -> None:
    viewport = _viewport(WorldBounds(0, 10, 0, 5))

    assert viewport.to_cell(0, 0) == (0, 10)
    assert viewport.to_cell(10, 5) == (20, 0)
    assert viewport.to_cell(0, 5) == (0, 0)
    assert viewport.to_cell(10, 0) == (20, 10)


def test_larger_world_y_is_drawn_higher() -> None:
    viewport = _viewport(WorldBounds(0, 10, 0, 10))

    _, low_row = viewport.to_cell(5, 1)
    _, high_row = viewport.to_cell(5, 9)

    assert high_row < low_row


def test_midpoint_maps_to_center() -> None:
    viewport = _viewport(WorldBounds(0, 10, 0, 10))

    assert viewport.to_screen(5, 5) == (10.0, 5.0)


def test_negative_coordinates() -> None:
    viewport = _viewport(WorldBounds(-4, 4, -2, 2))

    assert viewport.to_cell(-4, 2) == (0, 0)
    assert viewport.to_cell(4, -2) == (20, 10)
    assert viewport.to_cell(0, 0) == (10, 5)


def test_degenerate_x_axis_is_centered() -> None:
    viewport = _viewport(WorldBounds(3, 3, 0, 10))

    assert viewport.to_cell(3, 0) == (10, 10)
    assert viewport.to_cell(3, 10) == (10, 0)


def test_degenerate_y_axis_is_centered() -> None:
    viewport = _viewport(WorldBounds(0, 10, 7, 7))

    assert viewport.to_cell(0, 7) == (0, 5)
    assert viewport.to_cell(10, 7) == (20, 5)


def test_single_point_map_is_centered_on_both_axes() -> None:
    viewport = _viewport(WorldBounds(1, 1, 1, 1))

    assert viewport.to_cell(1, 1) == (10, 5)


def test_margins_are_preserved() -> None:
    viewport = Viewport(WorldBounds(0, 10, 0, 10), 21, 11, margin_x=3, margin_y=2)

    assert viewport.to_cell(0, 10) == (3, 2)
    assert viewport.to_cell(10, 0) == (17, 8)


def test_margins_shrink_when_viewport_is_tiny() -> None:
    viewport = Viewport(WorldBounds(0, 10, 0, 10), 3, 2, margin_x=5, margin_y=5)

    for world in ((0, 0), (10, 10), (5, 5)):
        x, y = viewport.to_cell(*world)
        assert 0 <= x < 3
        assert 0 <= y < 2


def test_resize_rescales_positions() -> None:
    bounds = WorldBounds(0, 10, 0, 10)

    small = _viewport(bounds, width=11, height=11)
    large = _viewport(bounds, width=41, height=21)

    assert small.to_cell(10, 0) == (10, 10)
    assert large.to_cell(10, 0) == (40, 20)
    assert large.to_cell(5, 5) == (20, 10)


def test_out_of_bounds_world_coordinates_are_clamped() -> None:
    viewport = _viewport(WorldBounds(0, 10, 0, 10))

    assert viewport.to_cell(-100, 100) == (0, 0)
    assert viewport.to_cell(100, -100) == (20, 10)


def test_rounding_is_half_up() -> None:
    viewport = _viewport(WorldBounds(0, 4, 0, 0), width=3, height=1)

    # world x=1 -> screen 0.5, x=3 -> 1.5: both ties round up.
    assert viewport.to_cell(1, 0) == (1, 0)
    assert viewport.to_cell(3, 0) == (2, 0)
