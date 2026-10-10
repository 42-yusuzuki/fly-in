"""CLI entry point for Fly-in."""

import sys
from pathlib import Path

from flyin.parser.errors import FlyInParseError
from flyin.parser.parser import FlyInParser
from flyin.simulation.formatter import SimulationFormatter
from flyin.simulation.simulation import Simulation
from flyin.solver.errors import FlyInSolutionError
from flyin.solver.solver import FlyInSolver
from flyin.visualization.graphical import GraphicalVisualizer
from flyin.visualization.gui.app import run_gui
from flyin.visualization.terminal import TerminalVisualizer
from flyin.visualization.tui.app import run_visualizer

_USAGE = "Usage: fly-in <map_file> [--gui | --html-gui | --visualize]"
_VALID_FLAGS = {"--gui", "--html-gui", "--visualize"}


def main() -> None:
    """Run Fly-in."""
    if len(sys.argv) not in (2, 3) or (
        len(sys.argv) == 3 and sys.argv[2] not in _VALID_FLAGS
    ):
        print(_USAGE)
        raise SystemExit(1)

    flag = sys.argv[2] if len(sys.argv) == 3 else None
    map_path = Path(sys.argv[1])

    try:
        flyin_map = FlyInParser().parse(map_path)
    except FlyInParseError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    try:
        solution = FlyInSolver().solve(flyin_map)
    except FlyInSolutionError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    simulation = Simulation(paths=solution.paths)

    TerminalVisualizer().display(simulation)
    print()
    print(SimulationFormatter().format(simulation))

    if flag == "--html-gui":
        visualizer = GraphicalVisualizer()
        output_path = Path("flyin_visualization.html")
        visualizer.render(flyin_map, simulation, output_path)
        print(f"\nGraphical visualization written to {output_path}")
        visualizer.open_in_browser(output_path)
    elif flag == "--gui":
        run_gui(flyin_map, simulation)
    elif flag == "--visualize":
        run_visualizer(flyin_map, simulation, map_path.name)


if __name__ == "__main__":
    main()
