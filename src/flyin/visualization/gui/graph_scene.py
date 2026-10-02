"""Qt graphics scene rendering the Fly-in network and drone positions."""

import math

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsScene

from flyin.domain.map import FlyInMap
from flyin.simulation.drone_path import DroneStep
from flyin.simulation.simulation import Simulation
from flyin.visualization.gui.connection_item import ConnectionItem
from flyin.visualization.gui.drone_item import DroneItem
from flyin.visualization.gui.zone_item import ZoneItem

_WIDTH = 860.0
_HEIGHT = 560.0
_PADDING = 70.0
_JITTER_RADIUS = 14.0
_JITTER_GROUP_PRECISION = 1.0


class GraphScene(QGraphicsScene):
    """Owns the static network layout and the per-turn drone positions.

    This class only *reads* `FlyInMap` and `Simulation` -- it never
    recomputes a route, decomposes flow, or mutates either one.
    `Simulation` remains the sole source of truth for where each drone
    is at a given turn; this scene is purely a display of that data.
    """

    def __init__(self, flyin_map: FlyInMap, simulation: Simulation) -> None:
        """Build the static scene and position drones at turn 0.

        Args:
            flyin_map: Map to draw zones and connections from.
            simulation: Already-solved simulation to display.
        """
        super().__init__()
        self._map = flyin_map
        self._simulation = simulation
        self._positions = self._layout_zones()
        self._drone_items: dict[int, DroneItem] = {}
        self._current_turn = 0

        self.setSceneRect(0, 0, _WIDTH, _HEIGHT)
        self._build_connections()
        self._build_zones()
        self._build_drones()
        self.render_turn(0)

    @property
    def max_turn(self) -> int:
        """Return the simulation's final turn number."""
        return self._simulation.total_turns

    @property
    def current_turn(self) -> int:
        """Return the turn currently committed (not mid-animation)."""
        return self._current_turn

    def zone_position(self, name: str) -> QPointF:
        """Return the scene position of a zone, by name."""
        return self._positions[name]

    def drone_position(self, drone_id: int) -> QPointF:
        """Return a drone's current displayed scene position."""
        return self._drone_items[drone_id].pos()

    def render_turn(self, turn: int) -> None:
        """Snap every drone directly to its position at `turn` (no animation)."""
        turn = self._clamp(turn)
        targets = {
            path.drone_id: self._position_for_step(path.step_at(turn))
            for path in self._simulation.paths
        }
        self._place_drones(targets)
        self._current_turn = turn

    def interpolate(self, target_turn: int, fraction: float) -> None:
        """Blend every drone's position between the current and target turn.

        This only moves the displayed `DroneItem`s; it does not change
        `current_turn`. Call `commit_turn` once the animation finishes
        to advance the authoritative turn.

        Args:
            target_turn: Turn being animated toward.
            fraction: Progress through the transition, clamped to [0, 1].
        """
        fraction = min(max(fraction, 0.0), 1.0)
        target_turn = self._clamp(target_turn)

        start_points = {
            path.drone_id: self._position_for_step(path.step_at(self._current_turn))
            for path in self._simulation.paths
        }
        end_points = {
            path.drone_id: self._position_for_step(path.step_at(target_turn))
            for path in self._simulation.paths
        }
        blended = {
            drone_id: start + (end_points[drone_id] - start) * fraction
            for drone_id, start in start_points.items()
        }
        self._place_drones(blended)

    def commit_turn(self, turn: int) -> None:
        """Finalize a transition by snapping exactly to `turn`."""
        self.render_turn(turn)

    def _place_drones(self, base_positions: dict[int, QPointF]) -> None:
        for drone_id, point in self._apply_jitter(base_positions).items():
            self._drone_items[drone_id].setPos(point)

    def _clamp(self, turn: int) -> int:
        return min(max(turn, 0), self.max_turn)

    def _position_for_step(self, step: DroneStep) -> QPointF:
        """Resolve a drone step to a scene point (zone or connection midpoint)."""
        if step.on_connection:
            source, _, destination = step.location.partition("-")
            return (self._positions[source] + self._positions[destination]) / 2
        return self._positions[step.location]

    def _apply_jitter(self, points: dict[int, QPointF]) -> dict[int, QPointF]:
        """Spread drones sharing a base position so none fully overlap."""
        groups: dict[tuple[int, int], list[int]] = {}
        for drone_id, point in points.items():
            key = (
                round(point.x() / _JITTER_GROUP_PRECISION),
                round(point.y() / _JITTER_GROUP_PRECISION),
            )
            groups.setdefault(key, []).append(drone_id)

        result: dict[int, QPointF] = {}
        for drone_ids in groups.values():
            drone_ids.sort()
            count = len(drone_ids)
            for index, drone_id in enumerate(drone_ids):
                base = points[drone_id]
                if count == 1:
                    result[drone_id] = base
                    continue
                angle = 2 * math.pi * index / count
                offset = QPointF(
                    math.cos(angle) * _JITTER_RADIUS,
                    math.sin(angle) * _JITTER_RADIUS,
                )
                result[drone_id] = base + offset
        return result

    def _layout_zones(self) -> dict[str, QPointF]:
        """Normalize each zone's (x, y) map coordinate into a scene point."""
        zones = list(self._map.zones.values())
        xs = [zone.x for zone in zones]
        ys = [zone.y for zone in zones]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        positions: dict[str, QPointF] = {}
        for zone in zones:
            normalized_x = (zone.x - min_x) / span_x
            normalized_y = (zone.y - min_y) / span_y
            x = _PADDING + normalized_x * (_WIDTH - 2 * _PADDING)
            # Flip Y so increasing map-y goes up on screen, not down.
            y = (_HEIGHT - _PADDING) - normalized_y * (_HEIGHT - 2 * _PADDING)
            positions[zone.name] = QPointF(x, y)
        return positions

    def _build_zones(self) -> None:
        for zone in self._map.zones.values():
            point = self._positions[zone.name]
            item = ZoneItem(
                zone,
                point.x(),
                point.y(),
                is_start=zone.name == self._map.start,
                is_goal=zone.name == self._map.goal,
            )
            self.addItem(item)

    def _build_connections(self) -> None:
        for connection in self._map.connections:
            item = ConnectionItem(
                connection,
                self._positions[connection.source],
                self._positions[connection.destination],
            )
            self.addItem(item)

    def _build_drones(self) -> None:
        for path in self._simulation.paths:
            item = DroneItem(path.drone_id)
            self.addItem(item)
            self._drone_items[path.drone_id] = item
