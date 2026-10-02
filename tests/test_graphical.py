"""Tests for the graphical (HTML) visualizer."""

from pathlib import Path

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.graphical import GraphicalVisualizer


def _flyin_map() -> FlyInMap:
    return FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={
            "A": Zone(name="A", x=0, y=0, zone_type=ZoneType.NORMAL, max_drones=5),
            "B": Zone(name="B", x=1, y=0, zone_type=ZoneType.NORMAL, max_drones=5),
        },
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )


def _simulation() -> Simulation:
    return Simulation(
        paths=[
            DronePath(
                drone_id=1,
                steps=[
                    DroneStep(turn=0, location="A"),
                    DroneStep(turn=1, location="B"),
                ],
            ),
        ],
    )


def test_render_writes_a_self_contained_html_file(tmp_path: Path) -> None:
    """The renderer should write one HTML file embedding the drone data."""
    output_path = tmp_path / "out.html"

    GraphicalVisualizer().render(_flyin_map(), _simulation(), output_path)

    html = output_path.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert '"name": "A"' in html
    assert '"name": "B"' in html
    assert '"source": "A"' in html
    assert '"destination": "B"' in html
    assert '"id": 1' in html
    assert "D1-B" in html  # embedded plain-text move line


def test_render_handles_zero_drones(tmp_path: Path) -> None:
    """An empty simulation must still render without error."""
    output_path = tmp_path / "out.html"

    GraphicalVisualizer().render(_flyin_map(), Simulation(paths=[]), output_path)

    assert output_path.exists()
    assert '"drones": []' in output_path.read_text(encoding="utf-8")
