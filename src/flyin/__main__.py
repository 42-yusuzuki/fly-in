"""CLI entry point for Fly-in."""

import sys
from pathlib import Path

from flyin.parser.errors import FlyInParseError
from flyin.parser.parser import FlyInParser
from flyin.simulation.formatter import SimulationFormatter
from flyin.simulation.simulation import Simulation
from flyin.solver.errors import FlyInSolutionError
from flyin.solver.solver import FlyInSolver
from flyin.visualization.terminal import TerminalVisualizer


def main() -> None:
    """Run Fly-in."""
    if len(sys.argv) != 2:
        print("Usage: fly-in <map_file>")
        raise SystemExit(1)

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


if __name__ == "__main__":
    main()
