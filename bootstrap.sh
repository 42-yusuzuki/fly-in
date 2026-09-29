#!/usr/bin/env bash

set -euo pipefail

ROOT="${1:-.}"

echo "Initializing Fly-in project in: $ROOT"

# ------------------------------------------------------------
# Directories
# ------------------------------------------------------------

mkdir -p \
    "$ROOT/src/flyin/domain" \
    "$ROOT/src/flyin/parser" \
    "$ROOT/src/flyin/graph" \
    "$ROOT/src/flyin/solver" \
    "$ROOT/src/flyin/simulation" \
    "$ROOT/src/flyin/visualization" \
    "$ROOT/tests" \
    "$ROOT/maps/simple" \
    "$ROOT/maps/edge_cases" \
    "$ROOT/maps/subject"

# ------------------------------------------------------------
# __init__.py
# ------------------------------------------------------------

touch \
    "$ROOT/src/flyin/__init__.py" \
    "$ROOT/src/flyin/domain/__init__.py" \
    "$ROOT/src/flyin/parser/__init__.py" \
    "$ROOT/src/flyin/graph/__init__.py" \
    "$ROOT/src/flyin/solver/__init__.py" \
    "$ROOT/src/flyin/simulation/__init__.py" \
    "$ROOT/src/flyin/visualization/__init__.py"

# ------------------------------------------------------------
# pyproject.toml
# ------------------------------------------------------------

cat > "$ROOT/pyproject.toml" <<'EOF'
[project]
name = "fly-in"
version = "0.1.0"
description = "Drone routing simulation for the 42 Fly-in project"
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
fly-in = "flyin.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/flyin"]

[dependency-groups]
dev = [
    "flake8>=7.0",
    "mypy>=1.10",
    "pytest>=8.0",
]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
ignore_missing_imports = true
disallow_untyped_defs = true
check_untyped_defs = true
files = ["src", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
EOF

# ------------------------------------------------------------
# .flake8
# ------------------------------------------------------------

cat > "$ROOT/.flake8" <<'EOF'
[flake8]
max-line-length = 88
exclude =
    .venv,
    .git,
    __pycache__,
    dist,
    build
EOF

# ------------------------------------------------------------
# .gitignore
# ------------------------------------------------------------

cat > "$ROOT/.gitignore" <<'EOF'
.venv/
__pycache__/
*.py[cod]

.pytest_cache/
.mypy_cache/

build/
dist/
*.egg-info/

.DS_Store
EOF

# ------------------------------------------------------------
# Makefile
# ------------------------------------------------------------

cat > "$ROOT/Makefile" <<'EOF'
.PHONY: install run debug clean lint lint-strict test build

install:
	uv sync

run:
	uv run fly-in $(ARGS)

debug:
	uv run python -m pdb -m flyin $(ARGS)

lint:
	uv run flake8 .
	uv run mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest

build:
	uv build

clean:
	rm -rf \
		.pytest_cache \
		.mypy_cache \
		build \
		dist
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
EOF

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/__main__.py" <<'EOF'
"""CLI entry point for Fly-in."""

import sys


def main() -> None:
    """Run Fly-in."""
    if len(sys.argv) != 2:
        print("Usage: fly-in <map_file>")
        raise SystemExit(1)

    map_path = sys.argv[1]

    # TODO:
    # 1. Parse map
    # 2. Solve routing problem
    # 3. Build simulation
    # 4. Output visualization

    print(f"map: {map_path}")


if __name__ == "__main__":
    main()
EOF

# ------------------------------------------------------------
# Domain
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/domain/zone.py" <<'EOF'
"""Zone domain models."""

from dataclasses import dataclass
from enum import Enum


class ZoneType(Enum):
    """Fly-in zone type."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Zone:
    """A zone in the Fly-in map."""

    name: str
    x: int
    y: int
    zone_type: ZoneType
    max_drones: int
EOF

cat > "$ROOT/src/flyin/domain/connection.py" <<'EOF'
"""Connection domain model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """A bidirectional connection between zones."""

    connection_id: int
    source: str
    destination: str
    max_capacity: int
EOF

cat > "$ROOT/src/flyin/domain/map.py" <<'EOF'
"""Fly-in map domain model."""

from dataclasses import dataclass

from flyin.domain.connection import Connection
from flyin.domain.zone import Zone


@dataclass(frozen=True)
class FlyInMap:
    """Complete parsed Fly-in map."""

    drone_count: int
    start: str
    goal: str
    zones: dict[str, Zone]
    connections: list[Connection]
EOF

# ------------------------------------------------------------
# Parser
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/parser/errors.py" <<'EOF'
"""Parser exceptions."""


class FlyInParseError(Exception):
    """Raised when a Fly-in map cannot be parsed."""
EOF

cat > "$ROOT/src/flyin/parser/parser.py" <<'EOF'
"""Fly-in map parser."""

from pathlib import Path

from flyin.domain.map import FlyInMap


class FlyInParser:
    """Parse Fly-in input files."""

    def parse(self, path: Path) -> FlyInMap:
        """Parse a map file.

        Args:
            path: Input map path.

        Returns:
            Parsed FlyInMap.
        """
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Generic flow graph
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/graph/flow_graph.py" <<'EOF'
"""Generic residual flow graph."""

from dataclasses import dataclass


@dataclass
class FlowEdge:
    """Residual graph edge."""

    to: int
    rev: int
    capacity: int
    original_capacity: int


class FlowGraph:
    """Directed residual graph."""

    def __init__(self, node_count: int) -> None:
        """Initialize graph."""
        self.adjacency: list[list[FlowEdge]] = [
            [] for _ in range(node_count)
        ]

    def add_edge(self, source: int, target: int, capacity: int) -> None:
        """Add a residual edge pair."""
        forward = FlowEdge(
            to=target,
            rev=len(self.adjacency[target]),
            capacity=capacity,
            original_capacity=capacity,
        )

        reverse = FlowEdge(
            to=source,
            rev=len(self.adjacency[source]),
            capacity=0,
            original_capacity=0,
        )

        self.adjacency[source].append(forward)
        self.adjacency[target].append(reverse)
EOF

cat > "$ROOT/src/flyin/graph/dinic.py" <<'EOF'
"""Dinic maximum-flow algorithm."""

from flyin.graph.flow_graph import FlowGraph


class Dinic:
    """Maximum-flow solver using Dinic's algorithm."""

    def __init__(self, graph: FlowGraph) -> None:
        """Initialize solver."""
        self.graph = graph

    def max_flow(self, source: int, sink: int) -> int:
        """Calculate maximum flow."""
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Solver states
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/solver/states.py" <<'EOF'
"""States used by the time-expanded network."""

from dataclasses import dataclass
from enum import Enum


class NodeSide(Enum):
    """Side of a vertex-split zone."""

    IN = "in"
    OUT = "out"


@dataclass(frozen=True)
class ZoneState:
    """Zone state at a particular simulation turn."""

    zone_name: str
    turn: int
    side: NodeSide


@dataclass(frozen=True)
class ConnectionState:
    """Connection state at a particular simulation turn."""

    connection_id: int
    turn: int
EOF

# ------------------------------------------------------------
# Time-expanded network
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/solver/time_expanded.py" <<'EOF'
"""Construction of the Fly-in time-expanded network."""

from dataclasses import dataclass

from flyin.domain.map import FlyInMap
from flyin.graph.flow_graph import FlowGraph


@dataclass
class TimeExpandedNetwork:
    """Generated flow network with source/sink metadata."""

    graph: FlowGraph
    source: int
    sink: int


class TimeExpandedNetworkBuilder:
    """Translate a Fly-in map into a time-expanded flow network."""

    def build(
        self,
        flyin_map: FlyInMap,
        max_turns: int,
    ) -> TimeExpandedNetwork:
        """Build the network for a fixed time horizon."""
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Simulation route models
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/simulation/drone_path.py" <<'EOF'
"""Drone route models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DroneStep:
    """One drone state during a simulation turn."""

    turn: int
    location: str
    on_connection: bool = False


@dataclass(frozen=True)
class DronePath:
    """Path assigned to one drone."""

    drone_id: int
    steps: list[DroneStep]
EOF

# ------------------------------------------------------------
# Solver result
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/solver/solution.py" <<'EOF'
"""Solver result models."""

from dataclasses import dataclass

from flyin.simulation.drone_path import DronePath


@dataclass(frozen=True)
class Solution:
    """Final routing solution."""

    turns: int
    paths: list[DronePath]
EOF

# ------------------------------------------------------------
# Main solver
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/solver/solver.py" <<'EOF'
"""High-level Fly-in solver."""

from flyin.domain.map import FlyInMap
from flyin.solver.solution import Solution


class FlyInSolver:
    """Find a minimum-turn solution for all drones."""

    def solve(self, flyin_map: FlyInMap) -> Solution:
        """Solve a Fly-in map."""
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Flow decomposition
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/solver/decomposer.py" <<'EOF'
"""Convert network flow into individual drone paths."""

from flyin.graph.flow_graph import FlowGraph
from flyin.simulation.drone_path import DronePath


class FlowDecomposer:
    """Decompose integral flow into individual drone routes."""

    def decompose(
        self,
        graph: FlowGraph,
        source: int,
        sink: int,
        drone_count: int,
    ) -> list[DronePath]:
        """Extract one path for each drone."""
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Simulation
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/simulation/simulation.py" <<'EOF'
"""Fly-in simulation representation."""

from dataclasses import dataclass

from flyin.simulation.drone_path import DronePath


@dataclass(frozen=True)
class Simulation:
    """Complete turn-by-turn simulation."""

    paths: list[DronePath]

    @property
    def total_turns(self) -> int:
        """Return total number of simulation turns."""
        if not self.paths:
            return 0

        return max(
            step.turn
            for path in self.paths
            for step in path.steps
        )
EOF

cat > "$ROOT/src/flyin/simulation/formatter.py" <<'EOF'
"""Subject-compatible simulation output."""

from flyin.simulation.simulation import Simulation


class SimulationFormatter:
    """Format a simulation using Fly-in output syntax."""

    def format(self, simulation: Simulation) -> str:
        """Format the complete simulation."""
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Visualization
# ------------------------------------------------------------

cat > "$ROOT/src/flyin/visualization/terminal.py" <<'EOF'
"""Terminal visualization."""

from flyin.simulation.simulation import Simulation


class TerminalVisualizer:
    """Display Fly-in simulation state in the terminal."""

    def display(self, simulation: Simulation) -> None:
        """Display simulation."""
        raise NotImplementedError
EOF

# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

cat > "$ROOT/tests/test_dinic.py" <<'EOF'
"""Tests for Dinic maximum flow."""


def test_placeholder() -> None:
    """Placeholder until Dinic is implemented."""
    assert True
EOF

cat > "$ROOT/tests/test_time_expanded.py" <<'EOF'
"""Tests for the time-expanded network."""


def test_placeholder() -> None:
    """Placeholder until network builder is implemented."""
    assert True
EOF

cat > "$ROOT/tests/test_parser.py" <<'EOF'
"""Tests for the Fly-in parser."""


def test_placeholder() -> None:
    """Placeholder until parser is implemented."""
    assert True
EOF

cat > "$ROOT/tests/test_simulation.py" <<'EOF'
"""Tests for simulation/output."""


def test_placeholder() -> None:
    """Placeholder until simulation is implemented."""
    assert True
EOF

# ------------------------------------------------------------
# README
# ------------------------------------------------------------

if [ ! -f "$ROOT/README.md" ]; then
    cat > "$ROOT/README.md" <<'EOF'
# Fly-in

Drone routing simulation for the 42 curriculum.

## Development

```bash
make install
make test
make lint
```

Run a map:

```bash
make run ARGS="maps/simple/example.map"
```
EOF
fi

# ------------------------------------------------------------
# uv
# ------------------------------------------------------------

echo
echo "Project structure created."

if command -v uv >/dev/null 2>&1; then
    echo "Running uv sync..."
    (
        cd "$ROOT"
        uv sync
    )
else
    echo "uv was not found; skipping dependency installation."
fi

echo
echo "Done."
echo
echo "Next commands:"
echo "  cd $ROOT"
echo "  make test"
echo "  make lint"
