"""Timeline bar: playhead, turn ticks, and click-to-seek."""

from rich.text import Text
from textual.events import Click
from textual.message import Message
from textual.widget import Widget

from flyin.visualization.tui import palette

#: Tick spacings tried in order; the first that keeps labels apart wins.
_TICK_STEPS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)
_PLAYHEAD = "●"
_PLAYED = "━"
_UNPLAYED = "─"


def column_of(position: float, width: int, last_turn: int) -> int:
    """Return the bar column for a (fractional) turn position."""
    if width <= 1 or last_turn <= 0:
        return 0
    ratio = min(max(position / last_turn, 0.0), 1.0)
    return round(ratio * (width - 1))


def turn_at(column: int, width: int, last_turn: int) -> int:
    """Return the turn nearest to a bar column (inverse of column_of)."""
    if width <= 1 or last_turn <= 0:
        return 0
    ratio = min(max(column / (width - 1), 0.0), 1.0)
    return round(ratio * last_turn)


def tick_step(width: int, last_turn: int) -> int:
    """Return the smallest tick spacing whose labels do not touch."""
    if last_turn <= 0 or width <= 1:
        return 1
    label_room = len(str(last_turn)) + 1
    cells_per_turn = (width - 1) / last_turn
    for step in _TICK_STEPS:
        if step * cells_per_turn >= label_room:
            return step
    return _TICK_STEPS[-1]


def build_timeline_text(width: int, last_turn: int, position: float) -> Text:
    """Return the two-line timeline: the bar, then turn-number ticks.

    Args:
        width: Available columns.
        last_turn: Final turn of the simulation.
        position: Displayed turn, fractional while animating (turn
            ``t`` at progress ``p`` is ``t - 1 + p``).
    """
    text = Text(no_wrap=True, overflow="crop")
    if width <= 0:
        return text
    head = column_of(position, width, last_turn)
    text.append(_PLAYED * head, palette.ACTIVE_CONNECTION_STYLE)
    text.append(_PLAYHEAD, palette.HEADING_STYLE)
    text.append(_UNPLAYED * (width - head - 1), palette.CONNECTION_STYLE)
    text.append("\n")

    text.append(_tick_row(width, last_turn), palette.MUTED_STYLE)
    return text


def _tick_row(width: int, last_turn: int) -> str:
    """Return turn numbers under the bar, always including the last turn.

    Labels start at their turn's column (shifted left to fit) and keep
    at least one blank cell on each side; a tick that would touch an
    already placed label is skipped.
    """
    row = [" "] * width
    step = tick_step(width, last_turn)
    turns = [last_turn, *range(0, last_turn, step)]
    for turn in turns:
        label = str(turn)
        start = min(column_of(turn, width, last_turn), width - len(label))
        if start < 0:
            continue
        around = row[max(start - 1, 0):start + len(label) + 1]
        if any(cell != " " for cell in around):
            continue
        row[start:start + len(label)] = label
    return "".join(row)


class Timeline(Widget):
    """Two-row timeline; clicking it seeks to the nearest turn."""

    class Seek(Message):
        """Posted when the user clicks a turn on the timeline."""

        def __init__(self, turn: int) -> None:
            """Create the message for the turn that was clicked."""
            super().__init__()
            self.turn = turn

    def __init__(self, last_turn: int, widget_id: str | None = None) -> None:
        """Create a timeline at turn 0.

        Args:
            last_turn: Final turn of the simulation.
            widget_id: Optional Textual widget id.
        """
        super().__init__(id=widget_id)
        self._last_turn = last_turn
        self._position = 0.0

    def show(self, position: float) -> None:
        """Move the playhead to a (fractional) turn position."""
        if position != self._position:
            self._position = position
            self.refresh()

    def render(self) -> Text:
        """Return the bar and ticks for the current width."""
        return build_timeline_text(
            self.content_size.width, self._last_turn, self._position,
        )

    def on_click(self, event: Click) -> None:
        """Seek to the turn under the mouse."""
        offset = event.get_content_offset(self)
        if offset is None:
            return
        self.post_message(
            self.Seek(turn_at(offset.x, self.content_size.width, self._last_turn)),
        )
