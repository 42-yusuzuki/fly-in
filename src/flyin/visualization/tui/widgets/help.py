"""Modal help overlay listing the visualizer's controls."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from flyin.visualization.tui import palette

#: ``(keys, description)`` rows, grouped by blank ``("", "")`` rows.
HELP_ROWS = (
    ("Space", "Play / pause (from the end: replay)"),
    ("← / →", "Previous / next turn"),
    ("Home / End", "First / last turn"),
    ("+ / -", "Faster / slower (0.25x - 4x)"),
    ("R", "Restart at turn 0, paused"),
    ("", ""),
    ("Tab / Shift+Tab", "Select next / previous zone or link"),
    ("Click graph", "Select the zone or link under the mouse"),
    ("Click timeline", "Jump to that turn"),
    ("Esc", "Clear selection"),
    ("", ""),
    ("?", "Show / hide this help"),
    ("Q", "Quit"),
)
_KEY_COLUMN = 17


def build_help_text() -> Text:
    """Return the help overlay contents."""
    text = Text(no_wrap=True)
    text.append("Fly-in visualizer — controls\n\n", palette.HEADING_STYLE)
    for keys, description in HELP_ROWS:
        if not keys:
            text.append("\n")
            continue
        text.append(f"{keys:<{_KEY_COLUMN}}", "bold #fbbf24")
        text.append(f"{description}\n", palette.LABEL_STYLE)
    text.append("\nPress ? or Esc to close.", palette.MUTED_STYLE)
    return text


class HelpScreen(ModalScreen[None]):
    """Centered panel with the key bindings; any close key dismisses it."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        background: #0b1120 70%;
    }
    #help-box {
        width: auto;
        height: auto;
        padding: 1 2;
        background: #1e293b;
        border: round #38bdf8;
    }
    #help-text {
        width: auto;
    }
    """
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Lay out the help panel."""
        with Vertical(id="help-box"):
            yield Static(build_help_text(), id="help-text")
