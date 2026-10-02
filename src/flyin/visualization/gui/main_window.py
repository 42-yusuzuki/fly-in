"""Main Qt window: graph view, playback controls, and turn display."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from flyin.domain.map import FlyInMap
from flyin.simulation.simulation import Simulation
from flyin.visualization.gui.graph_scene import GraphScene

_ANIMATION_TICK_MS = 16
_MAX_ANIMATION_DURATION_MS = 350
_MIN_ANIMATION_DURATION_MS = 80
_SPEED_INTERVALS_MS = {"0.5x": 1600, "1x": 800, "2x": 400, "4x": 200}


class MainWindow(QMainWindow):
    """Top-level window hosting the graph view and simulation controls.

    Owns only display state (the currently shown turn and in-progress
    animation progress); `GraphScene`/`Simulation` remain the source of
    truth for where every drone actually is at a given turn.
    """

    def __init__(self, flyin_map: FlyInMap, simulation: Simulation) -> None:
        """Build the window around a read-only FlyInMap/Simulation pair."""
        super().__init__()
        self.setWindowTitle("Fly-in simulation")

        self._scene = GraphScene(flyin_map, simulation)
        self._playing = False
        self._interval_ms = _SPEED_INTERVALS_MS["1x"]
        self._animation_target = 0
        self._animation_elapsed_ms = 0

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._on_animation_tick)

        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._on_play_tick)

        self._turn_label = QLabel()
        self._play_button = QPushButton()
        self._build_ui()
        self._update_turn_label()

    def _build_ui(self) -> None:
        view = QGraphicsView(self._scene)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(view)
        layout.addLayout(self._build_controls())

        self.setCentralWidget(central)
        self.resize(940, 680)

    def _build_controls(self) -> QHBoxLayout:
        prev_button = QPushButton("« Prev")
        next_button = QPushButton("Next »")
        reset_button = QPushButton("Reset")
        speed_box = QComboBox()
        speed_box.addItems(list(_SPEED_INTERVALS_MS.keys()))
        speed_box.setCurrentText("1x")

        self._play_button.setText("▶ Play")
        prev_button.clicked.connect(self._on_prev)
        self._play_button.clicked.connect(self._on_play_pause)
        next_button.clicked.connect(self._on_next)
        reset_button.clicked.connect(self._on_reset)
        speed_box.currentTextChanged.connect(self._on_speed_changed)

        controls = QHBoxLayout()
        controls.addWidget(prev_button)
        controls.addWidget(self._play_button)
        controls.addWidget(next_button)
        controls.addWidget(reset_button)
        controls.addWidget(QLabel("Speed:"))
        controls.addWidget(speed_box)
        controls.addStretch(1)
        controls.addWidget(self._turn_label)
        return controls

    def _on_prev(self) -> None:
        self._stop_playing()
        self._go_to_turn(self._scene.current_turn - 1)

    def _on_next(self) -> None:
        self._stop_playing()
        self._go_to_turn(self._scene.current_turn + 1)

    def _on_reset(self) -> None:
        self._stop_playing()
        self._animation_timer.stop()
        self._scene.render_turn(0)
        self._update_turn_label()

    def _on_play_pause(self) -> None:
        if self._playing:
            self._stop_playing()
            return

        self._playing = True
        self._play_button.setText("⏸ Pause")
        if self._scene.current_turn >= self._scene.max_turn:
            self._animation_timer.stop()
            self._scene.render_turn(0)
            self._update_turn_label()
        self._play_timer.start(self._interval_ms)

    def _on_play_tick(self) -> None:
        if self._scene.current_turn >= self._scene.max_turn:
            self._stop_playing()
            return
        self._go_to_turn(self._scene.current_turn + 1)

    def _on_speed_changed(self, label: str) -> None:
        self._interval_ms = _SPEED_INTERVALS_MS[label]
        if self._playing:
            self._play_timer.start(self._interval_ms)

    def _stop_playing(self) -> None:
        self._playing = False
        self._play_timer.stop()
        self._play_button.setText("▶ Play")

    def _go_to_turn(self, target_turn: int) -> None:
        """Start an animated transition toward target_turn, if not already there."""
        target_turn = min(max(target_turn, 0), self._scene.max_turn)
        if target_turn == self._scene.current_turn:
            return
        if self._animation_timer.isActive() and target_turn == self._animation_target:
            return

        self._animation_target = target_turn
        self._animation_elapsed_ms = 0
        self._turn_label.setText(self._format_turn_label(target_turn))
        self._animation_timer.start(_ANIMATION_TICK_MS)

    def _on_animation_tick(self) -> None:
        self._animation_elapsed_ms += _ANIMATION_TICK_MS
        duration = self._animation_duration_ms()
        fraction = self._animation_elapsed_ms / duration
        if fraction >= 1.0:
            self._animation_timer.stop()
            self._scene.commit_turn(self._animation_target)
        else:
            self._scene.interpolate(self._animation_target, fraction)

    def _animation_duration_ms(self) -> int:
        """Shorten the per-turn animation at higher playback speeds."""
        return min(
            _MAX_ANIMATION_DURATION_MS,
            max(_MIN_ANIMATION_DURATION_MS, int(self._interval_ms * 0.6)),
        )

    def _update_turn_label(self) -> None:
        self._turn_label.setText(self._format_turn_label(self._scene.current_turn))

    def _format_turn_label(self, turn: int) -> str:
        return f"Turn {turn} / {self._scene.max_turn}"
