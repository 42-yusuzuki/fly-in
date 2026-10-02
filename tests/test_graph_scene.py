"""Unit tests for GraphScene's state-conversion logic (no pixel rendering)."""

from PySide6.QtWidgets import QApplication

from flyin.domain.connection import Connection
from flyin.domain.map import FlyInMap
from flyin.domain.zone import Zone, ZoneType
from flyin.simulation.drone_path import DronePath, DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.gui.graph_scene import GraphScene


def _app() -> None:
    """Ensure a QApplication exists; QGraphicsScene needs one to construct."""
    if QApplication.instance() is None:
        QApplication([])


def _zone(name: str, x: int, zone_type: ZoneType = ZoneType.NORMAL) -> Zone:
    return Zone(name=name, x=x, y=0, zone_type=zone_type, max_drones=5)


def _restricted_map() -> FlyInMap:
    return FlyInMap(
        drone_count=1,
        start="A",
        goal="R",
        zones={"A": _zone("A", 0), "R": _zone("R", 2, ZoneType.RESTRICTED)},
        connections=[Connection(1, "A", "R", max_capacity=5)],
    )


def test_zone_positions_follow_map_coordinates() -> None:
    """Zones further along the x-axis on the map stay further apart on screen."""
    _app()
    flyin_map = FlyInMap(
        drone_count=0,
        start="left",
        goal="right",
        zones={"left": _zone("left", 0), "right": _zone("right", 10)},
        connections=[],
    )
    scene = GraphScene(flyin_map, Simulation(paths=[]))

    assert scene.zone_position("left").x() < scene.zone_position("right").x()


def test_drone_position_matches_its_zone_at_each_turn() -> None:
    """Rendering a turn places the drone exactly at that turn's zone."""
    _app()
    flyin_map = _restricted_map()
    simulation = Simulation(
        paths=[
            DronePath(
                drone_id=1,
                steps=[
                    DroneStep(turn=0, location="A"),
                    DroneStep(turn=1, location="A-R", on_connection=True),
                    DroneStep(turn=2, location="R"),
                ],
            ),
        ],
    )
    scene = GraphScene(flyin_map, simulation)

    scene.render_turn(0)
    assert scene.drone_position(1) == scene.zone_position("A")

    scene.render_turn(2)
    assert scene.drone_position(1) == scene.zone_position("R")


def test_restricted_connection_transit_places_drone_at_midpoint() -> None:
    """While in flight toward a restricted zone, the drone sits mid-connection."""
    _app()
    flyin_map = _restricted_map()
    simulation = Simulation(
        paths=[
            DronePath(
                drone_id=1,
                steps=[
                    DroneStep(turn=0, location="A"),
                    DroneStep(turn=1, location="A-R", on_connection=True),
                    DroneStep(turn=2, location="R"),
                ],
            ),
        ],
    )
    scene = GraphScene(flyin_map, simulation)

    scene.render_turn(1)

    expected = (scene.zone_position("A") + scene.zone_position("R")) / 2
    assert scene.drone_position(1) == expected


def test_drones_sharing_a_zone_are_spread_apart() -> None:
    """Two drones in the same capacity>1 zone must not fully overlap."""
    _app()
    flyin_map = FlyInMap(
        drone_count=2,
        start="A",
        goal="B",
        zones={"A": _zone("A", 0), "B": _zone("B", 5)},
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )
    simulation = Simulation(
        paths=[
            DronePath(drone_id=1, steps=[DroneStep(turn=0, location="A")]),
            DronePath(drone_id=2, steps=[DroneStep(turn=0, location="A")]),
        ],
    )
    scene = GraphScene(flyin_map, simulation)
    scene.render_turn(0)

    assert scene.drone_position(1) != scene.drone_position(2)


def test_drone_that_reached_goal_stays_put_on_later_turns() -> None:
    """A delivered drone's displayed position does not move past its arrival."""
    _app()
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={"A": _zone("A", 0), "B": _zone("B", 5)},
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )
    simulation = Simulation(
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
    scene = GraphScene(flyin_map, simulation)

    scene.render_turn(1)
    arrived_at = scene.drone_position(1)

    scene.render_turn(5)  # beyond this drone's recorded path
    assert scene.drone_position(1) == arrived_at
    assert arrived_at == scene.zone_position("B")


def test_interpolate_does_not_change_current_turn() -> None:
    """Mid-animation interpolation must not advance the committed turn."""
    _app()
    flyin_map = FlyInMap(
        drone_count=1,
        start="A",
        goal="B",
        zones={"A": _zone("A", 0), "B": _zone("B", 5)},
        connections=[Connection(1, "A", "B", max_capacity=5)],
    )
    simulation = Simulation(
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
    scene = GraphScene(flyin_map, simulation)

    scene.interpolate(1, 0.5)

    assert scene.current_turn == 0
    midpoint = (scene.zone_position("A") + scene.zone_position("B")) / 2
    assert scene.drone_position(1) == midpoint
