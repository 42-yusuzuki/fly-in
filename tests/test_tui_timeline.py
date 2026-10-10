"""Tests for the timeline bar geometry and text."""

import pytest

from flyin.visualization.tui.widgets.timeline import (
    build_timeline_text,
    column_of,
    tick_step,
    turn_at,
)


@pytest.mark.parametrize(
    ("position", "expected"),
    [(0.0, 0), (5.0, 10), (10.0, 20), (2.5, 5), (-1.0, 0), (99.0, 20)],
)
def test_column_of(position: float, expected: int) -> None:
    assert column_of(position, 21, 10) == expected


def test_turn_at_inverts_column_of() -> None:
    for turn in range(11):
        assert turn_at(column_of(turn, 41, 10), 41, 10) == turn


def test_degenerate_timelines_stay_at_turn_zero() -> None:
    assert column_of(3.0, 20, 0) == 0
    assert turn_at(15, 20, 0) == 0
    assert column_of(3.0, 1, 10) == 0


def test_tick_step_grows_as_space_shrinks() -> None:
    assert tick_step(100, 10) == 1
    assert tick_step(60, 43) == 5
    assert tick_step(30, 200) == 50


def test_timeline_text_has_bar_and_ticks() -> None:
    lines = build_timeline_text(21, 10, 5.0).plain.split("\n")

    assert lines[0] == "━" * 10 + "●" + "─" * 10
    assert lines[1].startswith("0 ")
    assert lines[1].rstrip().endswith("10")


def test_last_turn_label_is_always_shown() -> None:
    ticks = build_timeline_text(60, 43, 0.0).plain.split("\n")[1]

    assert ticks.rstrip().endswith("43")
    assert "  " in ticks  # labels keep gaps between them


def test_zero_width_timeline_is_empty() -> None:
    assert build_timeline_text(0, 10, 0.0).plain == ""
