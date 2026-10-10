"""Tests for playback state and drone motion in the terminal visualizer."""

import pytest

from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.tui.animation import (
    SPEED_PRESETS,
    TURN_DURATION,
    Anchor,
    PlaybackController,
    drone_motion,
    interpolate,
    turn_motions,
)
from flyin.visualization.tui.snapshot import TurnSnapshot, build_snapshots


def _snapshots(*paths: list[str], transit: int | None = None) -> tuple[
    TurnSnapshot, ...,
]:
    """Build snapshots; ``transit`` marks that turn as on-connection."""
    simulation = Simulation(paths=[
        DronePath(
            drone_id=index + 1,
            steps=[
                DroneStep(turn, location, on_connection=turn == transit)
                for turn, location in enumerate(locations)
            ],
        )
        for index, locations in enumerate(paths)
    ])
    return build_snapshots(simulation, "g")


# --- PlaybackController ---------------------------------------------------


def test_controller_starts_paused_at_rest_on_turn_zero() -> None:
    playback = PlaybackController(3)

    assert (playback.turn, playback.progress, playback.playing) == (0, 1.0, False)
    assert playback.speed == 1.0
    assert playback.label == "Paused 1x"


def test_tick_advances_turns_and_interpolation() -> None:
    playback = PlaybackController(3)
    playback.toggle()

    playback.tick(TURN_DURATION * 0.25)
    assert playback.turn == 1
    assert playback.progress == pytest.approx(0.25)

    playback.tick(TURN_DURATION)
    assert playback.turn == 2
    assert playback.progress == pytest.approx(0.25)


def test_pause_freezes_progress() -> None:
    playback = PlaybackController(3)
    playback.toggle()
    playback.tick(TURN_DURATION * 0.5)
    playback.toggle()

    playback.tick(10.0)

    assert playback.turn == 1
    assert playback.progress == pytest.approx(0.5)
    assert not playback.playing


def test_playback_stops_at_last_turn_and_replays_from_start() -> None:
    playback = PlaybackController(2)
    playback.toggle()

    playback.tick(100.0)
    assert (playback.turn, playback.progress, playback.playing) == (2, 1.0, False)
    assert playback.at_end

    playback.toggle()
    assert (playback.turn, playback.playing) == (0, True)


def test_speed_scales_animation_not_turns() -> None:
    playback = PlaybackController(10)
    playback.faster()
    assert playback.speed == 2.0
    playback.toggle()

    playback.tick(TURN_DURATION * 0.25)

    assert playback.turn == 1
    assert playback.progress == pytest.approx(0.5)


def test_speed_presets_are_clamped() -> None:
    playback = PlaybackController(1)
    for _ in range(10):
        playback.faster()
    assert playback.speed == SPEED_PRESETS[-1]
    for _ in range(10):
        playback.slower()
    assert playback.speed == SPEED_PRESETS[0]


def test_stepping_shows_whole_turns_and_restart_pauses() -> None:
    playback = PlaybackController(3)
    playback.toggle()
    playback.tick(TURN_DURATION * 0.4)

    playback.step(1)
    assert (playback.turn, playback.progress) == (2, 1.0)
    playback.step(-5)
    assert playback.turn == 0
    playback.go_to(99)
    assert playback.turn == 3

    playback.restart()
    assert (playback.turn, playback.progress, playback.playing) == (0, 1.0, False)


def test_single_turn_simulation_never_plays() -> None:
    playback = PlaybackController(0)
    playback.toggle()

    assert not playback.playing


def test_negative_last_turn_is_rejected() -> None:
    with pytest.raises(ValueError):
        PlaybackController(-1)


# --- Motion ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("progress", "expected"),
    [
        (0.0, (0.0, 0.0)),
        (0.5, (5.0, 2.0)),
        (1.0, (10.0, 4.0)),
        (-1.0, (0.0, 0.0)),
        (2.0, (10.0, 4.0)),
    ],
)
def test_interpolate(progress: float, expected: tuple[float, float]) -> None:
    assert interpolate((0.0, 0.0), (10.0, 4.0), progress) == expected


def test_normal_move_goes_zone_to_zone() -> None:
    snapshots = _snapshots(["s", "A"])

    motion = drone_motion(snapshots[0].drones[0], snapshots[1].drones[0])

    assert motion is not None
    assert (motion.start, motion.end) == (Anchor("s"), Anchor("A"))


def test_restricted_transit_is_two_stages_through_the_midpoint() -> None:
    snapshots = _snapshots(["s", "s-R", "R"], transit=1)
    midpoint = Anchor.midpoint("s", "R")

    first = drone_motion(snapshots[0].drones[0], snapshots[1].drones[0])
    second = drone_motion(snapshots[1].drones[0], snapshots[2].drones[0])

    assert first is not None and second is not None
    assert (first.start, first.end) == (Anchor("s"), midpoint)
    assert (second.start, second.end) == (midpoint, Anchor("R"))


def test_midpoint_ignores_direction() -> None:
    assert Anchor.midpoint("b", "a") == Anchor.midpoint("a", "b") == Anchor("a", "b")


def test_waiting_and_turn_zero_drones_do_not_move() -> None:
    snapshots = _snapshots(["s", "s"])

    assert drone_motion(None, snapshots[0].drones[0]) is None
    assert drone_motion(snapshots[0].drones[0], snapshots[1].drones[0]) is None


def test_turn_motions_splits_movers_and_hides_delivered() -> None:
    snapshots = _snapshots(["s", "g", "g"], ["s", "s", "g"])

    motions, stationary = turn_motions(snapshots[1], snapshots[2])

    # Drone 1 was delivered earlier: neither moving nor drawn.
    assert [m.drone.drone_id for m in motions] == [2]
    assert motions[0].end == Anchor("g")
    assert stationary == ()

    motions, stationary = turn_motions(None, snapshots[0])
    assert motions == ()
    assert [d.drone_id for d in stationary] == [1, 2]
