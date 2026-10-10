"""Playback state and drone motion for the terminal visualizer.

Simulation time and animation time are separate: the simulation only
knows whole turns, while the visualizer adds a ``progress`` in
``[0.0, 1.0]`` that interpolates the move *into* the current turn.
``progress == 1.0`` is the logical state of the turn itself, and
``progress == 0.0`` looks exactly like the previous turn at rest.
Nothing here depends on Textual.
"""

from dataclasses import dataclass

from flyin.visualization.tui.snapshot import (
    DroneActivity,
    DroneSnapshot,
    TurnSnapshot,
)

#: Seconds one logical turn takes to animate at 1.0x speed.
TURN_DURATION = 0.6
SPEED_PRESETS = (0.25, 0.5, 1.0, 2.0, 4.0)
DEFAULT_SPEED_INDEX = SPEED_PRESETS.index(1.0)


class PlaybackController:
    """Own the displayed turn, interpolation progress, and play state.

    Rules (from the visualizer design):

    - pausing freezes ``progress``;
    - stepping to another turn shows that turn at rest (``progress`` 1);
    - reaching the last turn stops playback;
    - restart returns to turn 0, paused.
    """

    def __init__(self, last_turn: int) -> None:
        """Create a paused controller showing turn 0.

        Args:
            last_turn: Final turn of the simulation (0 or more).

        Raises:
            ValueError: If ``last_turn`` is negative.
        """
        if last_turn < 0:
            raise ValueError("last_turn must be 0 or more")
        self.last_turn = last_turn
        self.turn = 0
        self.progress = 1.0
        self.playing = False
        self._speed_index = DEFAULT_SPEED_INDEX

    @property
    def speed(self) -> float:
        """Return the playback speed multiplier."""
        return SPEED_PRESETS[self._speed_index]

    @property
    def label(self) -> str:
        """Return a short play-state and speed label, e.g. ``Playing 2x``."""
        state = "Playing" if self.playing else "Paused"
        return f"{state} {self.speed:g}x"

    @property
    def at_end(self) -> bool:
        """Return whether the last turn is fully displayed."""
        return self.turn == self.last_turn and self.progress >= 1.0

    def tick(self, elapsed: float) -> None:
        """Advance playback by ``elapsed`` wall-clock seconds."""
        if not self.playing or elapsed <= 0:
            return
        self.progress += elapsed * self.speed / TURN_DURATION
        while self.progress >= 1.0:
            if self.turn >= self.last_turn:
                self.progress = 1.0
                self.playing = False
                return
            self.turn += 1
            self.progress -= 1.0

    def toggle(self) -> None:
        """Play or pause; playing from the very end starts over."""
        if self.playing:
            self.playing = False
            return
        if self.at_end:
            self.turn = 0
            self.progress = 1.0
        self.playing = self.last_turn > 0

    def step(self, delta: int) -> None:
        """Show the turn ``delta`` turns away, at rest, clamped."""
        self.go_to(self.turn + delta)

    def go_to(self, turn: int) -> None:
        """Show ``turn`` at rest, clamped to the simulated range."""
        self.turn = min(max(turn, 0), self.last_turn)
        self.progress = 1.0

    def restart(self) -> None:
        """Return to turn 0 and pause."""
        self.go_to(0)
        self.playing = False

    def faster(self) -> None:
        """Select the next faster speed preset, if any."""
        self._speed_index = min(self._speed_index + 1, len(SPEED_PRESETS) - 1)

    def slower(self) -> None:
        """Select the next slower speed preset, if any."""
        self._speed_index = max(self._speed_index - 1, 0)


@dataclass(frozen=True)
class Anchor:
    """A point a drone moves from or to: a zone, or a connection's middle.

    Attributes:
        zone: Zone name, or the first endpoint of a connection.
        other: Second endpoint when the anchor is a connection midpoint.
    """

    zone: str
    other: str | None = None

    @classmethod
    def midpoint(cls, zone_a: str, zone_b: str) -> "Anchor":
        """Return the midpoint of a connection, independent of direction."""
        low, high = sorted((zone_a, zone_b))
        return cls(low, high)


@dataclass(frozen=True)
class DroneMotion:
    """Where a drone travels during the transition into a turn."""

    drone: DroneSnapshot
    start: Anchor
    end: Anchor


def drone_motion(
    previous: DroneSnapshot | None, current: DroneSnapshot,
) -> DroneMotion | None:
    """Return how a drone moves into ``current``, or ``None`` if it stays.

    A restricted transit is animated in two stages that match the
    simulation's two logical turns: origin zone to the connection's
    middle, then the middle to the restricted zone.

    Args:
        previous: The same drone at the previous turn (``None`` at
            turn 0).
        current: The drone at the turn being animated into.
    """
    if previous is None or current.link is None:
        return None
    source, target = current.link
    if current.activity is DroneActivity.IN_TRANSIT:
        return DroneMotion(current, Anchor(source), Anchor.midpoint(source, target))
    if previous.activity is DroneActivity.IN_TRANSIT:
        return DroneMotion(current, Anchor.midpoint(source, target), Anchor(target))
    return DroneMotion(current, Anchor(source), Anchor(target))


def turn_motions(
    previous: TurnSnapshot | None, current: TurnSnapshot,
) -> tuple[tuple[DroneMotion, ...], tuple[DroneSnapshot, ...]]:
    """Split ``current``'s drones into moving and stationary ones.

    Returns:
        ``(motions, stationary)`` where ``stationary`` only holds drones
        still drawn on the map.
    """
    before = (
        {drone.drone_id: drone for drone in previous.drones}
        if previous is not None else {}
    )
    motions: list[DroneMotion] = []
    stationary: list[DroneSnapshot] = []
    for drone in current.drones:
        motion = drone_motion(before.get(drone.drone_id), drone)
        if motion is not None:
            motions.append(motion)
        elif drone.on_map:
            stationary.append(drone)
    return tuple(motions), tuple(stationary)


def interpolate(
    start: tuple[float, float], end: tuple[float, float], progress: float,
) -> tuple[float, float]:
    """Return the point ``progress`` of the way from ``start`` to ``end``.

    ``progress`` is clamped to ``[0.0, 1.0]``; rounding to a cell is
    left to the caller.
    """
    p = min(max(progress, 0.0), 1.0)
    return (
        start[0] + (end[0] - start[0]) * p,
        start[1] + (end[1] - start[1]) * p,
    )
