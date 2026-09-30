"""Solver result models."""

from dataclasses import dataclass

from flyin.simulation.drone_path import DronePath


@dataclass(frozen=True)
class Solution:
    """Final routing solution."""

    turns: int
    paths: list[DronePath]
