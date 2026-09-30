"""Tests for Dinic maximum flow."""

from flyin.graph.dinic import Dinic
from flyin.graph.flow_graph import FlowGraph


def test_linear_graph() -> None:
    """Flow should be limited by the linear path capacity."""
    graph = FlowGraph(3)

    graph.add_edge(0, 1, 3)
    graph.add_edge(1, 2, 3)

    dinic = Dinic(graph)

    assert dinic.max_flow(0, 2) == 3


def test_parallel_paths() -> None:
    """Flow should use multiple independent paths."""
    graph = FlowGraph(4)

    graph.add_edge(0, 1, 1)
    graph.add_edge(1, 3, 1)

    graph.add_edge(0, 2, 1)
    graph.add_edge(2, 3, 1)

    dinic = Dinic(graph)

    assert dinic.max_flow(0, 3) == 2


def test_bottleneck() -> None:
    """Flow should be limited by the narrowest edge."""
    graph = FlowGraph(3)

    graph.add_edge(0, 1, 5)
    graph.add_edge(1, 2, 2)

    dinic = Dinic(graph)

    assert dinic.max_flow(0, 2) == 2
