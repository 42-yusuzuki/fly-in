"""Graphical (SVG/HTML) visualization of the network and drone positions.

Tkinter is unavailable in this project's interpreter (no system Tk
bindings installed), and a GUI toolkit would also be a poor fit for
peer review, where the reviewer's machine may have no display server at
all. A self-contained HTML file sidesteps both problems: it needs no
extra dependency beyond the standard library, and it opens in any
browser, including one on a different machine than the one that ran the
simulation.
"""

import json
import webbrowser
from pathlib import Path
from typing import Any

from flyin.domain.map import FlyInMap
from flyin.simulation.formatter import SimulationFormatter
from flyin.simulation.simulation import Simulation

_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Fly-in simulation</title>
<style>
  :root {
    --bg: #0f172a;
    --panel: #1e293b;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --line: #475569;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 40px;
  }
  h1 { font-size: 1.25rem; margin: 0 0 4px; }
  .subtitle { color: var(--muted); margin: 0 0 20px; font-size: 0.9rem; }
  #canvas-wrap {
    background: var(--panel);
    border-radius: 12px;
    padding: 12px;
    max-width: 100%;
  }
  svg { display: block; max-width: 100%; height: auto; }
  .zone-label { fill: var(--text); font-size: 11px; text-anchor: middle; }
  .zone-circle { stroke: #0f172a; stroke-width: 2; }
  .connection-line { stroke: var(--line); stroke-width: 2; }
  .drone-dot { stroke: #0f172a; stroke-width: 1.5; }
  .drone-label {
    font-size: 9px; fill: #0f172a; text-anchor: middle; font-weight: bold;
  }
  #controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    width: 100%;
    max-width: 640px;
  }
  button {
    background: var(--accent);
    border: none;
    border-radius: 6px;
    color: #0f172a;
    font-weight: bold;
    padding: 6px 14px;
    cursor: pointer;
  }
  button:hover { opacity: 0.85; }
  input[type="range"] { flex: 1; }
  #turn-label {
    min-width: 90px; text-align: right; font-variant-numeric: tabular-nums;
  }
  #moves {
    margin-top: 18px;
    width: 100%;
    max-width: 640px;
    background: var(--panel);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: var(--muted);
    white-space: pre-wrap;
  }
  .legend {
    display: flex; gap: 14px; margin-top: 10px;
    font-size: 0.8rem; color: var(--muted);
  }
  .legend span { display: inline-flex; align-items: center; gap: 4px; }
  .swatch { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
</style>
</head>
<body>
  <h1>Fly-in simulation</h1>
  <p class="subtitle">__SUBTITLE__</p>
  <div id="canvas-wrap"><svg id="svg" viewBox="0 0 860 560"></svg></div>
  <div id="controls">
    <button id="prev">&laquo;</button>
    <button id="play">&#9654; play</button>
    <button id="next">&raquo;</button>
    <input id="slider" type="range" min="0" max="0" value="0">
    <span id="turn-label">turn 0 / 0</span>
  </div>
  <div class="legend">
    <span><span class="swatch" style="background:#4a90d9"></span>normal</span>
    <span><span class="swatch" style="background:#2ecc71"></span>priority</span>
    <span><span class="swatch" style="background:#e74c3c"></span>restricted</span>
    <span><span class="swatch" style="background:#7f8c8d"></span>blocked</span>
  </div>
  <pre id="moves"></pre>

<script>
const DATA = __DATA_JSON__;
const ZONE_TYPE_COLORS = {
  normal: "#4a90d9", priority: "#2ecc71", restricted: "#e74c3c", blocked: "#7f8c8d",
};
const DRONE_COLORS = ["#ef4444", "#22c55e", "#eab308", "#3b82f6", "#a855f7", "#14b8a6"];
const RADIUS = 22, DRONE_RADIUS = 7, PAD = 50, W = 860, H = 560;

function layout() {
  const xs = DATA.zones.map(z => z.x), ys = DATA.zones.map(z => z.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = Math.max(maxX - minX, 1), spanY = Math.max(maxY - minY, 1);
  const pos = {};
  for (const z of DATA.zones) {
    const nx = (z.x - minX) / spanX, ny = (z.y - minY) / spanY;
    pos[z.name] = [PAD + nx * (W - 2 * PAD), H - (PAD + ny * (H - 2 * PAD))];
  }
  return pos;
}

const POS = layout();
const svg = document.getElementById("svg");
const ns = "http://www.w3.org/2000/svg";

function el(tag, attrs) {
  const node = document.createElementNS(ns, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

function drawNetwork() {
  for (const c of DATA.connections) {
    const [x1, y1] = POS[c.source], [x2, y2] = POS[c.destination];
    svg.appendChild(el("line", { x1, y1, x2, y2, class: "connection-line" }));
  }
  for (const z of DATA.zones) {
    const [x, y] = POS[z.name];
    const fill = z.color || ZONE_TYPE_COLORS[z.type] || "#4a90d9";
    const extra = (z.isStart || z.isGoal) ? 4 : 0;
    svg.appendChild(el("circle", {
      cx: x, cy: y, r: RADIUS + extra, fill, class: "zone-circle",
      "stroke-dasharray": z.isStart || z.isGoal ? "4 2" : "none",
    }));
    svg.appendChild(Object.assign(el("text", { x, y: y + 4, class: "zone-label" }), {
      textContent: z.name,
    }));
  }
}

const droneLayer = el("g", {});
svg.appendChild(droneLayer);

function framePosition(frame) {
  if (frame.zone !== undefined) return POS[frame.zone];
  const [x1, y1] = POS[frame.connection[0]], [x2, y2] = POS[frame.connection[1]];
  return [(x1 + x2) / 2, (y1 + y2) / 2];
}

function drawDrones(turn) {
  droneLayer.innerHTML = "";
  DATA.drones.forEach((drone, index) => {
    const frame = drone.frames[Math.min(turn, drone.frames.length - 1)];
    const [bx, by] = framePosition(frame);
    const offset = (index % 5) * 11 - 22;
    const x = bx + offset, y = by - RADIUS - 14;
    const color = DRONE_COLORS[index % DRONE_COLORS.length];
    droneLayer.appendChild(el("circle", {
      cx: x, cy: y, r: DRONE_RADIUS, fill: color, class: "drone-dot",
    }));
    const label = el("text", { x, y: y + 3, class: "drone-label" });
    droneLayer.appendChild(Object.assign(label, { textContent: "D" + drone.id }));
  });
}

const slider = document.getElementById("slider");
const turnLabel = document.getElementById("turn-label");
const movesBox = document.getElementById("moves");
const moveLines = DATA.movesText.split("\\n");

slider.max = DATA.totalTurns;

function render(turn) {
  turn = Math.max(0, Math.min(turn, DATA.totalTurns));
  slider.value = turn;
  turnLabel.textContent = `turn ${turn} / ${DATA.totalTurns}`;
  drawDrones(turn);
  movesBox.textContent = turn === 0
    ? "(start)"
    : (moveLines[turn - 1] || "(waiting)");
}

drawNetwork();
render(0);

document.getElementById("prev").onclick = () => render(+slider.value - 1);
document.getElementById("next").onclick = () => render(+slider.value + 1);
slider.oninput = () => render(+slider.value);

let playing = false, timer = null;
document.getElementById("play").onclick = (event) => {
  playing = !playing;
  event.target.textContent = playing ? "❚❚ pause" : "▶ play";
  if (playing) {
    timer = setInterval(() => {
      const nextTurn = +slider.value + 1;
      if (nextTurn > DATA.totalTurns) {
        playing = false;
        event.target.textContent = "▶ play";
        clearInterval(timer);
        return;
      }
      render(nextTurn);
    }, 700);
  } else {
    clearInterval(timer);
  }
};
</script>
</body>
</html>
"""


class GraphicalVisualizer:
    """Render the network and drone positions to a self-contained HTML file."""

    def render(
        self,
        flyin_map: FlyInMap,
        simulation: Simulation,
        output_path: Path,
    ) -> None:
        """Write an interactive HTML visualization to output_path.

        Args:
            flyin_map: Map used to draw zones and connections.
            simulation: Solved simulation used to animate drone
                positions turn by turn.
            output_path: File to write the HTML page to.
        """
        payload = self._build_payload(flyin_map, simulation)
        subtitle = (
            f"{len(flyin_map.zones)} zones, {len(flyin_map.connections)} "
            f"connections, {len(simulation.paths)} drone(s), "
            f"{simulation.total_turns} turn(s)"
        )
        html = _PAGE_TEMPLATE.replace("__SUBTITLE__", subtitle).replace(
            "__DATA_JSON__", json.dumps(payload)
        )
        output_path.write_text(html, encoding="utf-8")

    def open_in_browser(self, output_path: Path) -> None:
        """Open a previously rendered HTML file in the default browser."""
        webbrowser.open(output_path.resolve().as_uri())

    def _build_payload(
        self,
        flyin_map: FlyInMap,
        simulation: Simulation,
    ) -> dict[str, Any]:
        """Build the JSON-serializable data the page's JS renders from."""
        zones = [
            {
                "name": zone.name,
                "x": zone.x,
                "y": zone.y,
                "type": zone.zone_type.value,
                "color": zone.color,
                "isStart": zone.name == flyin_map.start,
                "isGoal": zone.name == flyin_map.goal,
            }
            for zone in flyin_map.zones.values()
        ]
        connections = [
            {
                "source": connection.source,
                "destination": connection.destination,
                "capacity": connection.max_capacity,
            }
            for connection in flyin_map.connections
        ]

        drones = []
        for path in simulation.paths:
            frames: list[dict[str, Any]] = []
            for turn in range(simulation.total_turns + 1):
                step = path.step_at(turn)
                if step.on_connection:
                    source, _, destination = step.location.partition("-")
                    frames.append({"connection": [source, destination]})
                else:
                    frames.append({"zone": step.location})
            drones.append({"id": path.drone_id, "frames": frames})

        return {
            "zones": zones,
            "connections": connections,
            "drones": drones,
            "totalTurns": simulation.total_turns,
            "movesText": SimulationFormatter().format(simulation),
        }
