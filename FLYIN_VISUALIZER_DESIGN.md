# Fly-in Terminal Visualizer Design

> Claude implementation handoff document
>
> This document defines the design of the terminal visualizer for the Fly-in project. Treat the decisions marked **MUST** as implementation constraints unless the project owner explicitly changes them.

---

## 1. Purpose

Fly-in requires a visual representation of the simulation. The subject explicitly allows either colored terminal output, a graphical interface, or both. The visualizer described here is a **terminal-based interactive simulator/debugger** implemented in Python.

The goal is not merely to print colored logs. The target experience is a modern graph viewer inside the terminal:

- zones are drawn as nodes using the coordinates from the map file;
- connections are drawn as edges;
- drones are animated while moving between zones;
- restricted-zone transit is shown as a multi-turn movement on the connection;
- zone and connection capacities are visible;
- the user can pause, step through turns, change playback speed, inspect a zone/connection, and restart;
- the visualizer helps explain and debug the solver without affecting solver behavior.

The visualizer should feel like a small **Fly-in Simulator / Debugger** rather than a decorative output mode.

---

## 2. Subject constraints that matter to this design

The following are requirements from the Fly-in subject and should be treated as hard constraints:

1. The project is written in Python 3.10 or later.
2. The project must be object-oriented and type-safe, with flake8 and mypy.
3. Graph-logic libraries such as `networkx` and `graphlib` are forbidden.
4. The implementation must provide visual feedback of the simulation through colored terminal output and/or a graphical representation.
5. Map zones have integer `x` and `y` coordinates.
6. Zone types include `normal`, `blocked`, `restricted`, and `priority`.
7. Zone capacity is controlled by `max_drones`; start/end have unlimited effective capacity.
8. Connection capacity is controlled by `max_link_capacity`.
9. Moving to a `restricted` destination costs 2 turns. During the intermediate turn, the drone occupies the connection and must arrive on the next turn; it cannot wait on the connection.
10. The normal simulation output format must still exist independently of the visualizer.

The visualizer is a presentation layer. It must not replace the mandatory simulation output formatter.

---

## 3. Existing project architecture

The current Fly-in architecture is organized around the following responsibilities:

```text
src/flyin/
├── domain/
├── parser/
├── graph/
├── solver/
├── simulation/
├── visualization/
└── __main__.py
```

Expected responsibility split:

```text
domain
    Zone / ZoneType / Connection / FlyInMap

parser
    input file -> FlyInMap

graph
    generic FlowGraph / FlowEdge / Dinic
    MUST NOT know Fly-in concepts

solver
    Time-Expanded Network
    minimum-turn search
    flow decomposition

simulation
    DronePath / DroneStep / per-turn state
    mandatory text formatter

visualization
    terminal UI and animation
```

The visualizer must fit this architecture rather than introduce solver/UI coupling.

---

## 4. Core architectural rule

### 4.1 One-way dependency

**MUST:** the visualizer is a read-only consumer of simulation results.

```text
FlyInMap
   +
Solution / Simulation
   |
   v
VisualizerModel
   |
   v
TerminalVisualizer
```

The dependency must never point back toward the solver.

Forbidden patterns:

```text
Visualizer -> Solver.run_again()
Visualizer -> Dinic internals
Visualizer -> TimeExpandedNetwork mutation
Solver -> Textual widgets
Domain -> rendering-specific fields
```

Allowed pattern:

```text
Solver produces deterministic simulation data.
Visualizer reads that data and decides only how to display/interpolate it.
```

### 4.2 Simulation time and animation time are different

This distinction is fundamental.

```text
simulation turn != animation frame
```

The solver reasons in discrete turns. The visualizer may render many frames between two turns.

Example:

```text
Turn 4 state -------------------- Turn 5 state
       frame 0
       frame 1
       frame 2
       frame 3
       frame 4
```

Animation interpolation must never create a new logical simulation state.

---

## 5. Proposed technology

### 5.1 Primary choice: Textual

Use the Python `textual` library for the interactive terminal UI.

Why:

- modern terminal layout system;
- keyboard input;
- optional mouse interaction;
- periodic refresh/timers;
- panels, status bars, lists, and sidebars;
- keeps the project entirely in Python;
- does not provide graph-solving logic, so all graph/pathfinding remains ours.

### 5.2 Rendering rule

**MUST:** graph drawing itself is custom code.

Textual may provide widgets/layout/events, but it must not decide graph paths, shortest paths, capacities, routing, or simulation states.

### 5.3 Fallback

If Textual later proves unacceptable for evaluation or dependency reasons, the same visualizer model must be reusable with a simpler ANSI/curses renderer.

For that reason, do not leak Textual classes into domain, solver, or simulation models.

---

## 6. Proposed module structure

```text
src/flyin/visualization/
├── __init__.py
├── app.py
├── model.py
├── viewport.py
├── canvas.py
├── animation.py
├── palette.py
├── widgets/
│   ├── __init__.py
│   ├── graph_view.py
│   ├── status_panel.py
│   ├── inspector.py
│   ├── timeline.py
│   └── help_bar.py
└── protocol.py
```

Suggested responsibilities:

### `model.py`

Presentation-specific immutable/read-only models derived from `FlyInMap` and `Simulation`.

### `viewport.py`

Coordinate transform between map coordinates and terminal cell coordinates.

### `canvas.py`

Low-level character-cell canvas and line/node/drone drawing helpers.

### `animation.py`

Frame interpolation and playback state.

### `palette.py`

Color/style mapping for zone types and dynamic states.

### `widgets/graph_view.py`

Main graph area.

### `widgets/status_panel.py`

Summary counts and current playback information.

### `widgets/inspector.py`

Selected zone/connection details.

### `widgets/timeline.py`

Current turn, stepping, progress visualization.

### `app.py`

Textual `App`; keybindings and top-level layout only.

---

## 7. Input contract from simulation layer

The visualizer should not infer movement by comparing arbitrary mutable objects if a cleaner explicit representation is available.

Preferred simulation-side contract:

```python
@dataclass(frozen=True)
class DroneLocation:
    kind: Literal["zone", "connection", "delivered"]
    name: str | None


@dataclass(frozen=True)
class DroneTurnState:
    drone_id: int
    location: DroneLocation


@dataclass(frozen=True)
class TurnState:
    turn: int
    drones: tuple[DroneTurnState, ...]


@dataclass(frozen=True)
class Simulation:
    turns: tuple[TurnState, ...]
```

If the simulation layer already has `DroneStep`, `DronePath`, etc., adapt rather than duplicate concepts unnecessarily.

The key requirement is that for every logical turn the visualizer can determine:

- each drone's source state;
- each drone's destination state;
- whether it is waiting;
- whether it is on a connection toward a restricted zone;
- whether it has been delivered.

---

## 8. Visualizer presentation model

Define a presentation model that is independent of Textual widgets.

Example:

```python
@dataclass(frozen=True)
class VisualZone:
    name: str
    world_x: int
    world_y: int
    zone_type: ZoneType
    max_drones: int | None
    color: str | None


@dataclass(frozen=True)
class VisualConnection:
    name: str
    zone_a: str
    zone_b: str
    max_capacity: int


@dataclass(frozen=True)
class DroneVisualState:
    drone_id: int
    source: DroneLocation
    target: DroneLocation
    progress: float  # 0.0 <= progress <= 1.0
```

`progress` belongs to visualization only. Never store it in the solver/simulation layer.

---

## 9. Screen layout

Target layout:

```text
┌────────────────────────────────────────────────────────────────────┐
│ Fly-in  hard_2.map       Turn 17 / 35        ▶ 1.0x               │
├─────────────────────────────────────────────┬──────────────────────┤
│                                             │ STATUS               │
│                                             │ Drones       12      │
│                                             │ Delivered     7      │
│                                             │ Moving        3      │
│                GRAPH VIEW                   │ Waiting       2      │
│                                             │ In transit    1      │
│                                             │                      │
│          ●────────────●                     │ SELECTED             │
│         ╱       D3     ╲                    │ corridor_A           │
│        ●                ●                   │ priority             │
│         ╲              ╱                    │ capacity 1 / 2       │
│          ●────────────●                     │                      │
│                                             │                      │
├─────────────────────────────────────────────┴──────────────────────┤
│ Timeline:  01 02 03 04 05 06 07 08 09 ...                        │
│                              ▲                                     │
├────────────────────────────────────────────────────────────────────┤
│ Space Play/Pause  ←/→ Turn  +/- Speed  Tab Select  R Reset  Q Quit │
└────────────────────────────────────────────────────────────────────┘
```

### Minimum terminal size

Define a reasonable minimum, for example:

```text
100 columns x 30 rows
```

If the terminal is smaller, show a concise error/overlay rather than rendering corrupted output.

---

## 10. Graph layout

### 10.1 Use map coordinates

The Fly-in input already provides integer `x`, `y` values for zones. Use them as the primary layout source.

Do **not** run an automatic force-directed graph layout.

### 10.2 World-to-screen transform

For the visible map bounds:

```text
min_x, max_x
min_y, max_y
```

map world coordinates into a graph viewport:

```text
screen_x = left + normalized_x * drawable_width
screen_y = top  + normalized_y * drawable_height
```

Preserve a margin around the graph.

### 10.3 Y-axis orientation

Map coordinates are conceptually Cartesian, while terminal rows increase downward.

Prefer:

```text
terminal_y = max_y - world_y
```

before normalization so larger map `y` values appear visually higher.

### 10.4 Degenerate ranges

If `min_x == max_x` or `min_y == max_y`, center zones on that axis rather than divide by zero.

### 10.5 Collision handling

Multiple zones can map to nearby terminal cells after scaling.

Required strategy:

1. compute ideal cell;
2. attempt local placement within a small radius;
3. keep zone labels secondary to nodes;
4. if labels overlap, truncate/hide labels before moving graph topology excessively.

Do not alter logical map coordinates.

---

## 11. Drawing primitives

Implement a small custom cell canvas abstraction.

Example API:

```python
class CellCanvas:
    def clear(self) -> None: ...
    def put(self, x: int, y: int, char: str, style: Style | None = None) -> None: ...
    def text(self, x: int, y: int, text: str, style: Style | None = None) -> None: ...
    def line(self, x1: int, y1: int, x2: int, y2: int, style: Style | None = None) -> None: ...
```

The line implementation may use a simple raster algorithm such as Bresenham.

Graph drawing priority:

```text
1. connections
2. connection metadata / capacity state
3. zones
4. zone labels
5. drones
6. selection/highlight overlay
```

Drones must visually sit above edges.

---

## 12. Zone rendering

Suggested default styles:

```text
start       green emphasis
end         yellow/gold emphasis
normal      blue/cyan
priority    green/cyan highlight
restricted  red/magenta
blocked     dim gray
```

The subject allows arbitrary map color strings. Map-provided color metadata should be respected where practical, but semantic state must remain understandable even when custom colors are unusual.

### 12.1 Capacity display

A selected zone should show:

```text
capacity: 1 / 2
```

Optionally show compact inline occupancy near a node if space permits.

### 12.2 Full capacity

A full zone should receive a strong visual emphasis (e.g. bold/high-contrast style).

Do not rely on color alone; inspector text should expose the numeric capacity.

---

## 13. Connection rendering

Each connection is bidirectional in the domain model.

Base appearance:

```text
●────────────●
```

Capacity-aware inspector:

```text
A <-> B
capacity: 2
occupied: 1 / 2
```

### 13.1 Full connection

If `max_link_capacity` is fully consumed for the current turn/frame, emphasize the edge.

### 13.2 Simultaneous drones

When multiple drones occupy/traverse the same connection, offset their displayed positions slightly so they remain individually identifiable.

For example:

```text
●────D1──D2────●
```

Exact visual offset is presentation-only.

---

## 14. Drone animation model

### 14.1 Normal one-turn movement

Given zone centers `(x1, y1)` and `(x2, y2)` and frame progress `p`:

```text
x = x1 + (x2 - x1) * p
y = y1 + (y2 - y1) * p
```

Clamp `p` to `[0.0, 1.0]`.

Round only at final cell placement.

### 14.2 Waiting

A waiting drone remains visually on its zone for the entire turn transition.

Optionally show a subtle wait marker in the inspector/status panel rather than animating it.

### 14.3 Delivered

A drone that reaches end can:

1. animate to end;
2. briefly highlight;
3. disappear from active graph rendering;
4. remain counted under `Delivered`.

### 14.4 Restricted movement

This must reflect the actual simulation semantics.

The simulation has an intermediate connection state.

Conceptually:

```text
Turn t      : drone at A
Turn t + 1  : drone on connection A-B
Turn t + 2  : drone at restricted B
```

Visualizer behavior:

```text
t -> t+1     animate A toward connection midpoint
state t+1    drone remains on connection
(t+1)->t+2   animate midpoint toward B
```

Do not fake restricted movement as a single extra-slow one-turn animation.

The intermediate logical connection occupancy is valuable debugging information and should be visible.

---

## 15. Frame clock and playback

Recommended playback model:

```text
logical_turn_duration = 0.6 seconds at 1.0x
frame_rate            = 20-30 FPS
```

Exact numbers can be tuned.

Playback speed presets:

```text
0.25x
0.5x
1.0x
2.0x
4.0x
```

The animation controller should own:

```python
class PlaybackController:
    current_turn: int
    progress: float
    speed: float
    playing: bool
```

Rules:

- pause freezes `progress`;
- right arrow moves to the next whole turn;
- left arrow moves to the previous whole turn;
- manual stepping resets interpolation progress;
- reaching the last turn stops playback;
- restart moves to turn 0 and pauses or returns to a defined default state.

---

## 16. Interaction design

Required keyboard controls:

```text
Space       play / pause
Right       next turn
Left        previous turn
+ / =       increase playback speed
-           decrease playback speed
R           restart
Tab         cycle selectable entities
Enter       inspect/select focused entity
Esc         clear selection / close overlay
Q           quit
?           show help overlay
```

Optional:

```text
Mouse click      select zone/connection
Mouse wheel      zoom or scroll inspector
```

Keyboard functionality should be sufficient by itself.

---

## 17. Inspector panel

### Zone selection

Show:

```text
Zone: corridor_A
Type: priority
Map coordinate: (4, 3)
Capacity: 1 / 2
Drones:
  D3
Connections:
  roof1       0 / 1
  tunnelB     1 / 2
```

### Connection selection

Show:

```text
Connection: corridor_A <-> tunnelB
Capacity: 2
Occupied: 2 / 2
Drones:
  D4 corridor_A -> tunnelB
  D7 tunnelB -> corridor_A
```

### Drone selection (optional, later milestone)

Show:

```text
Drone D4
State: in transit
From: corridor_A
To: roof1
Started: turn 7
Expected arrival: turn 8
```

---

## 18. Status panel

At minimum display:

```text
Map
Current turn / total turns
Playback speed
Total drones
Delivered
At zone / idle
Moving
Waiting
In restricted transit
```

Avoid computing solver metrics inside UI widgets. Derive status from simulation snapshots.

---

## 19. Timeline

Initial version can be simple:

```text
Turn 07 / 31
[=======-----------------------]
```

Later version may show numbered turns and marks for major events.

The timeline is informational and may also become interactive later, but click-to-seek is not required in MVP.

---

## 20. Styling principles

Target visual character:

- dark background;
- restrained neon accents;
- readable first, flashy second;
- selected entity should be obvious;
- blocked zones visually subdued;
- capacity saturation should be highly visible;
- avoid excessive animation unrelated to simulation state.

The UI should resemble a professional graph/database/network inspector rather than a game HUD.

---

## 21. CLI integration

Do not make the visualizer the only output path.

Suggested CLI:

```text
fly-in map.txt
fly-in map.txt --visualize
fly-in map.txt --visualize --speed 2.0
```

Possible later aliases:

```text
fly-in map.txt --ui
fly-in map.txt --no-animation
```

Default behavior should remain compatible with the mandatory textual simulation output unless the project owner explicitly chooses otherwise.

A robust pattern is:

```text
solve -> Simulation
           ├── SimulationFormatter -> stdout mandatory output
           └── TerminalVisualizer  -> interactive presentation
```

The exact UX of whether both run in the same command should be decided carefully so the evaluator can still capture the required output easily.

---

## 22. Performance rules

The visualizer must not materially slow down the solver.

**MUST:** solve first, visualize second.

Do not couple rendering FPS to Dinic/flow computation.

For large maps:

- cache world-to-screen zone positions until viewport size changes;
- cache connection raster paths until viewport changes;
- redraw only at the visualizer's frame rate;
- avoid rebuilding simulation snapshots every frame;
- keep animation calculations O(number of active drones + visible edges/nodes) per frame.

Do not prematurely optimize with complicated rendering architecture. Correctness and clean separation matter more.

---

## 23. Error handling

The visualizer should fail gracefully.

Cases to handle:

- terminal too small;
- invalid/missing simulation data;
- zero-turn simulation;
- map where all x coordinates are equal;
- map where all y coordinates are equal;
- very long zone names;
- too many drones to label individually at once;
- Textual initialization failure.

The visualizer failing must not corrupt solver results.

Consider allowing fallback to plain formatter output if the UI cannot start.

---

## 24. Testing strategy

### 24.1 Unit tests

Test without launching a real terminal whenever possible.

#### Coordinate transform

- min/max coordinates;
- negative coordinates;
- one-axis degenerate maps;
- resize behavior;
- clamping to viewport bounds.

#### Animation interpolation

- progress 0.0;
- progress 0.5;
- progress 1.0;
- horizontal/vertical/diagonal edges;
- normal movement;
- waiting;
- delivered transition;
- restricted transit two-stage behavior.

#### Capacity derivation

- zone occupancy count;
- start/end special handling;
- connection occupancy count;
- full/not-full states.

### 24.2 Snapshot/render tests

For the custom canvas, render tiny deterministic maps and compare expected character grids.

Example fixture:

```text
start(0,0) -- A(5,0) -- goal(10,0)
```

### 24.3 Integration tests

Given a known `Simulation`, confirm:

- stepping changes turn;
- pause freezes progress;
- restart returns to turn 0;
- speed changes animation duration, not logical states.

### 24.4 Manual evaluation tests

Run at least:

- simple linear map;
- fork with simultaneous drones;
- capacity bottleneck;
- restricted-zone transit;
- connection capacity > 1;
- large hard map.

---

## 25. Implementation milestones

### Milestone 1 — Static graph viewer

Implement:

- Textual app shell;
- map-coordinate scaling;
- node drawing;
- edge drawing;
- semantic zone styling;
- status panel with map metadata.

No drone movement yet.

Acceptance:

> A map file can be opened and its topology is recognizable inside the terminal.

### Milestone 2 — Turn snapshots

Implement:

- read `Simulation` states;
- render drones at zones/connections for a selected turn;
- next/previous turn controls;
- delivered/waiting/in-transit counts.

Acceptance:

> The user can inspect every logical turn without animation.

### Milestone 3 — Animation

Implement:

- frame clock;
- interpolation for normal movement;
- explicit two-stage restricted transit animation;
- play/pause;
- speed controls;
- restart.

Acceptance:

> A full simulation can be watched from start to finish and remains faithful to logical turns.

### Milestone 4 — Inspector

Implement:

- zone selection;
- connection selection;
- capacity/occupancy details;
- focused highlight.

Acceptance:

> The visualizer is useful for debugging capacity behavior.

### Milestone 5 — Polish

Implement selectively:

- mouse interaction;
- better collision handling;
- improved labels;
- timeline polish;
- help overlay;
- optional drone inspection.

---

## 26. Non-goals

Do not implement these as part of the initial visualizer:

- graph/pathfinding algorithms;
- automatic route optimization;
- editing the Fly-in map;
- changing simulation results from the UI;
- Web/React frontend;
- 3D drone graphics;
- physics simulation;
- force-directed layout;
- solver execution frame-by-frame.

A visualizer should visualize an already-computed Fly-in simulation.

---

## 27. Rules for Claude while implementing

Claude should follow these constraints strictly:

1. **Do not change solver behavior merely to simplify visualization.**
2. **Do not introduce graph-solving libraries.**
3. **Do not place Textual imports outside the visualization package unless there is a compelling entry-point reason.**
4. **Do not store animation progress in domain/simulation objects.**
5. **Do not infer restricted transit incorrectly; honor the connection state produced by the simulation.**
6. **Do not remove or replace the mandatory text output formatter.**
7. **Keep every new public function/class typed and documented.**
8. **Add tests for coordinate transforms and animation logic before visual polish.**
9. **Prefer small pure helper functions/classes for geometry and interpolation.**
10. **If existing project code differs from names in this design, adapt to the existing architecture rather than duplicating equivalent models.**
11. **Before coding, inspect the current `domain`, `simulation`, and `visualization` packages and summarize the actual interfaces that already exist.**
12. **After each milestone, run flake8, mypy, and tests.**

---

## 28. Recommended first implementation task for Claude

Do not start with animation.

Start with this exact task:

> Inspect the existing Fly-in repository. Do not modify solver behavior. Implement Milestone 1 only: a static Textual terminal graph viewer under `src/flyin/visualization/` that consumes the existing `FlyInMap`, scales its integer map coordinates into a resizable terminal viewport, draws connections and zones, styles zone types, and shows a small status panel. Add focused tests for coordinate transformation. Do not implement drone animation, inspector interaction, or solver integration beyond the minimum necessary to display an already-parsed map. Run flake8, mypy, and the existing test suite afterward and report any architecture mismatches between this design document and the current codebase.

This keeps the first change auditable and prevents the UI from becoming entangled with unfinished solver work.

---

## 29. Final target

The final visualizer should make a Fly-in run visually understandable at a glance:

```text
map topology
+ zone type
+ zone capacity
+ connection capacity
+ drone positions
+ drone movements
+ waiting
+ restricted transit
+ delivered count
+ timeline
```

The visualizer is successful when it answers debugging questions such as:

```text
Why is D4 waiting?
Which zone is saturated?
Which connection is the bottleneck?
Is a drone correctly spending a turn in restricted transit?
Are two drones using the same connection within capacity?
At which turn does congestion begin?
```

without requiring the developer to manually reconstruct state from log lines.
