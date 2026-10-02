"""PySide6 GUI application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from flyin.domain.map import FlyInMap
from flyin.simulation.simulation import Simulation
from flyin.visualization.gui.main_window import MainWindow


def run_gui(flyin_map: FlyInMap, simulation: Simulation) -> None:
    """Launch the PySide6 GUI for an already-solved simulation.

    The solver has already run by the time this is called; this
    function only displays the resulting `FlyInMap`/`Simulation` pair
    and never recomputes a route.

    Args:
        flyin_map: Map used to draw the static network.
        simulation: Solved simulation to display and step through.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(flyin_map, simulation)
    window.show()
    app.exec()
