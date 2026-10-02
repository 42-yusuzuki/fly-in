"""Tests for the Fly-in parser."""

from pathlib import Path

import pytest

from flyin.domain.zone import ZoneType
from flyin.parser.errors import FlyInParseError
from flyin.parser.parser import FlyInParser


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "map.flyin"
    path.write_text(content)
    return path


def test_parses_subject_example(tmp_path: Path) -> None:
    """The subject's worked example should parse without error."""
    content = """
    nb_drones: 5

    start_hub: hub 0 0 [color=green]
    end_hub: goal 10 10 [color=yellow]
    hub: roof1 3 4 [zone=restricted color=red]
    hub: roof2 6 2 [zone=normal color=blue]
    hub: corridorA 4 3 [zone=priority color=green max_drones=2]
    hub: tunnelB 7 4 [zone=normal color=red]
    hub: obstacleX 5 5 [zone=blocked color=gray]
    connection: hub-roof1
    connection: hub-corridorA
    connection: roof1-roof2
    connection: roof2-goal
    connection: corridorA-tunnelB [max_link_capacity=2]
    connection: tunnelB-goal
    """
    flyin_map = FlyInParser().parse(_write(tmp_path, content))

    assert flyin_map.drone_count == 5
    assert flyin_map.start == "hub"
    assert flyin_map.goal == "goal"
    assert set(flyin_map.zones) == {
        "hub", "goal", "roof1", "roof2", "corridorA", "tunnelB", "obstacleX",
    }
    assert flyin_map.zones["roof1"].zone_type == ZoneType.RESTRICTED
    assert flyin_map.zones["corridorA"].max_drones == 2
    assert flyin_map.zones["roof2"].max_drones == 1
    assert len(flyin_map.connections) == 6

    tunnel_connection = next(
        c for c in flyin_map.connections if c.source == "corridorA"
    )
    assert tunnel_connection.max_capacity == 2


def test_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    """Comment-only and blank lines should be skipped."""
    content = """
    # a full map with a bit of everything commented
    nb_drones: 1

    # start / end
    start_hub: a 0 0
    end_hub: b 1 0

    connection: a-b
    """
    flyin_map = FlyInParser().parse(_write(tmp_path, content))
    assert flyin_map.drone_count == 1
    assert len(flyin_map.connections) == 1


def test_missing_nb_drones_raises(tmp_path: Path) -> None:
    """A map without 'nb_drones' must fail to parse."""
    content = "start_hub: a 0 0\nend_hub: b 1 0\nconnection: a-b\n"
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_duplicate_zone_name_raises(tmp_path: Path) -> None:
    """Two zones sharing a name must be rejected."""
    content = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "hub: a 2 0\n"
        "connection: a-b\n"
    )
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_invalid_zone_type_raises(tmp_path: Path) -> None:
    """An unrecognized zone type must be rejected."""
    content = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0 [zone=lava]\n"
        "connection: a-b\n"
    )
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_connection_to_undefined_zone_raises(tmp_path: Path) -> None:
    """A connection naming an unknown zone must be rejected."""
    content = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-ghost\n"
    )
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_duplicate_connection_raises(tmp_path: Path) -> None:
    """The same connection declared twice (in either order) must fail."""
    content = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-b\n"
        "connection: b-a\n"
    )
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_dash_in_zone_name_raises(tmp_path: Path) -> None:
    """Zone names must not contain dashes."""
    content = "nb_drones: 1\nstart_hub: a-1 0 0\nend_hub: b 1 0\n"
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_missing_start_or_end_hub_raises(tmp_path: Path) -> None:
    """A map without both a start and an end hub must fail."""
    content = "nb_drones: 1\nstart_hub: a 0 0\n"
    with pytest.raises(FlyInParseError):
        FlyInParser().parse(_write(tmp_path, content))


def test_max_drones_metadata_ignored_on_start_and_end(tmp_path: Path) -> None:
    """Invalid-looking max_drones metadata on start/end must not error."""
    content = (
        "nb_drones: 1\n"
        "start_hub: a 0 0 [max_drones=0]\n"
        "end_hub: b 1 0 [max_drones=-3]\n"
        "connection: a-b\n"
    )
    flyin_map = FlyInParser().parse(_write(tmp_path, content))
    assert flyin_map.start == "a"
    assert flyin_map.goal == "b"
