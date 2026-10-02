*This project has been created as part of the 42 curriculum by yusuzuki.*

# fly-in

## Description

Fly-in routes a fleet of drones from a shared **start** zone to a shared
**end** zone across a network of connected zones, in the fewest possible
simulation turns, while respecting zone capacity, connection capacity, and
the extra travel time imposed by restricted zones.

The problem is modeled as a **maximum-flow problem over a time-expanded
graph**: every (zone, turn) pair becomes a node, and every legal drone
action (move, wait, or transit a restricted connection) becomes an edge
with the right capacity. Finding the minimum number of turns that lets
every drone reach the goal then reduces to: "what is the smallest `T` for
which max-flow(source → sink) in the `T`-turn network equals the number of
drones?" — answered with a doubling + binary search over `T`, each probe
solved with Dinic's algorithm.

## Instructions

```bash
make install        # uv sync
make run ARGS=maps/subject-example.flyin
make test           # pytest
make lint           # flake8 + mypy
make lint-strict     # flake8 + mypy --strict
make clean           # remove caches/build artifacts
```

A handful of hand-written sample maps live in `maps/`:

- `maps/subject-example.flyin` — the worked example from the subject
  itself (Chapter VI).
- `maps/easy-linear.flyin`, `maps/easy-fork.flyin`,
  `maps/easy-capacity.flyin` — small maps matching the "Easy" performance
  benchmarks (§VII.7).

## Example

Input (`maps/easy-fork.flyin`):

```
nb_drones: 4

start_hub: start 0 0
hub: junction 1 0
hub: pathA 2 1
hub: pathB 2 -1
end_hub: goal 3 0

connection: start-junction
connection: junction-pathA
connection: junction-pathB
connection: pathA-goal
connection: pathB-goal
```

Output (`make run ARGS=maps/easy-fork.flyin`, colors omitted here):

```
Simulation complete in 6 turn(s).

turn   1: D4-junction
turn   2: D3-junction D4-pathA
turn   3: D2-junction D3-pathA D4-goal
turn   4: D1-junction D2-pathA D3-goal
turn   5: D1-pathA D2-goal
turn   6: D1-goal
```

(`junction` defaults to `max_drones=1`, so the four drones serialize
through it one at a time — 6 turns, within the subject's `<= 8` target.)

## Technical choices and implementation strategy

- **Domain layer** (`domain/`) — plain, immutable dataclasses (`Zone`,
  `Connection`, `FlyInMap`) with no behavior. They are the only thing the
  parser produces and the only thing the solver consumes.
- **Parser** (`parser/`) — a single-pass, line-oriented reader. Each line
  is comment-stripped, trimmed, and dispatched by its prefix
  (`nb_drones:`, `start_hub:`/`end_hub:`/`hub:`, `connection:`). Every
  rule from §VII.4 (unique start/end, no dashes in names, connections
  only to already-declared zones, no duplicate `a-b`/`b-a` pairs, valid
  zone types, positive capacities, `max_drones` ignored on start/end) is
  enforced as it is encountered, and any violation raises
  `FlyInParseError` naming the offending line.
- **Graph layer** (`graph/`) — a generic residual `FlowGraph` plus
  `Dinic`, with zero knowledge of drones, zones or turns. No external
  graph library is used, per the subject's constraints (§V).
- **Time-expanded network** (`solver/time_expanded.py`) — the Fly-in
  rules are translated into the generic flow graph here, and nowhere
  else:
  - each zone is vertex-split into an `IN`/`OUT` pair per turn, with the
    `IN -> OUT` edge capped at `max_drones` (unlimited for start/end), so
    the max-flow algorithm can never route more drones through a zone at
    once than it allows;
  - an `OUT@t -> IN@(t+1)` edge lets a drone wait in place;
  - each bidirectional connection becomes a small gadget: a shared `hub`
    edge caps *combined* traffic in either direction at
    `max_link_capacity`, then each direction continues on its own lane —
    one turn later for a `normal`/`priority` destination, two turns later
    (via an explicit "in flight" node) for a `restricted` one, matching
    the movement costs in §VII.3.
- **Solver** (`solver/solver.py`) — the minimum feasible turn count is
  found by doubling an upper bound on `T` until a full max-flow of
  `drone_count` is achievable, then binary-searching down to the exact
  minimum. This relies on max-flow being **monotonically non-decreasing**
  in `T` (every edge of the `T`-turn network is still present, unchanged,
  in the `(T+1)`-turn network), which also bounds the number of Dinic
  calls to `O(log T)`.
- **Flow decomposition** (`solver/decomposer.py`) — the time-expanded
  network is a DAG, so after Dinic has run, one unit-flow path per drone
  can be peeled off greedily: repeatedly follow any edge that still
  carries flow (`original_capacity - capacity > 0`), consuming one unit
  of it, until the sink is reached. Each path is then translated from
  graph node ids back into `(turn, zone-or-connection)` steps, stopping
  as soon as the goal is reached (delivered drones are no longer
  tracked, per §VII.5).
- **Formatter** (`simulation/formatter.py`) — turns the raw per-turn
  state of every drone into the subject's output syntax, dropping any
  turn where a drone's location did not change (i.e. it waited), per
  §VII.5.
- **Complexity**: for `Z` zones, `C` connections and a search bound `T`,
  each time-expanded network has `O(Z*T)` nodes and `O((Z+C)*T)` edges;
  Dinic on it runs in `O(V^2*E)` worst case, and the minimum-turns search
  issues `O(log T)` such calls. In practice the graphs built here are far
  from the worst case (unit-ish capacities, short augmenting paths), so
  all provided benchmark maps solve in well under a second.

## Visual representation

`visualization/terminal.py` prints the simulation turn by turn, coloring
each `D<id>-<location>` entry by drone id (ANSI colors, cycling through
six hues) so that simultaneous, overlapping drone movements stay easy to
tell apart at a glance in the terminal. It is built on top of
`SimulationFormatter`, so the colored view and the plain subject-format
output are guaranteed to show exactly the same turns and moves.

## Resources

- Dinic's algorithm: *Algorithm for solution of a problem of maximum flow
  in a network with power estimation*, Y. Dinic (1970); CLRS
  (*Introduction to Algorithms*), chapter on flow networks.
- Time-expanded / time-indexed network flow formulations for scheduling
  problems with time-dependent capacities (a standard technique for
  "move multiple agents through a shared network over discrete time
  steps" problems).

**AI usage**: Claude (Anthropic) was used as a pair-programming aid for:
reading and summarizing this project's subject PDF into a structured
spec; writing the parser, solver, flow-decomposer, formatter and
terminal-visualization modules against that spec and the existing
`graph`/`domain` code; and writing the accompanying `pytest` test suite.
The existing `graph/` (generic `FlowGraph` + `Dinic`) and
`solver/time_expanded.py` modules predate this AI-assisted session. All
generated code was reviewed, run against `make lint-strict` and
`make test`, and exercised end-to-end against the maps in `maps/` before
being accepted.
