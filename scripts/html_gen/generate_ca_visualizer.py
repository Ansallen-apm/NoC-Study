import json
import os

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoC Cycle-Accurate Trace Visualizer</title>
    <style>
        body { font-family: sans-serif; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; background: #f5f6fa;}
        #toolbar { padding: 15px; background: #2c3e50; color: white; display: flex; gap: 10px; align-items: center;}
        button { padding: 8px 16px; cursor: pointer; background: #3498db; border: none; color: white; border-radius: 4px; }
        button:hover { background: #2980b9; }
        #canvas-container { flex-grow: 1; position: relative; overflow: auto; padding: 20px; }
        canvas { background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-radius: 8px; }
        #info-panel { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.9); padding: 15px; border-radius: 8px; border: 1px solid #ddd; max-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .cycle-text { font-size: 1.2em; font-weight: bold; margin-left: 20px; }
        input[type=range] { width: 300px; }
    </style>
</head>
<body>

<div id="toolbar">
    <button id="btn-prev">Prev Cycle</button>
    <button id="btn-play">Play / Pause</button>
    <button id="btn-next">Next Cycle</button>
    <input type="range" id="cycle-slider" min="0" value="0">
    <span class="cycle-text">Cycle: <span id="lbl-cycle">0</span> / <span id="lbl-max-cycle">0</span></span>
</div>

<div id="canvas-container">
    <canvas id="noc-canvas"></canvas>
    <div id="info-panel">
        <h3>Node Info</h3>
        <div id="node-details">Hover over a node to see buffer status.</div>
    </div>
</div>

<script>
    const traceData = {TRACE_DATA};

    const canvas = document.getElementById('noc-canvas');
    const ctx = canvas.getContext('2d');

    // Derived UI state
    let currentCycleIdx = 0;
    let playing = false;
    let playInterval = null;
    let nodePositions = {};

    // Layout parameters
    const GRID_SIZE = 80;
    const MARGIN = 50;

    // Auto-layout based on names
    function generateLayout() {
        // Find max x and y
        let maxX = 0, maxY = 0;

        traceData.topology.nodes.forEach(n => {
            // Rough heuristic for 3x3
            // Assuming vertical rings are 0,1,2 and horizontal are 3,4,5
            // Actually, rings 0,1,2 are vertical. Stations 0..11
            // This is a bit specific to our generation, but let's try a simple spring or grid layout.
            // For now, let's just arrange them in a large circle or grid by parsing ID.

            // Very hacky grid layout
            let x = Math.random() * 800;
            let y = Math.random() * 800;

            let parts = n.id.split('_');
            if (parts.length >= 2 && parts[0].startsWith('R')) {
                let r_id = parseInt(parts[0].substring(1));
                let s_id = parseInt(parts[1].substring(1));

                if (r_id < 3) { // Vertical
                    x = r_id * 3 * GRID_SIZE + MARGIN;
                    y = s_id * GRID_SIZE + MARGIN;
                } else { // Horizontal
                    y = (r_id - 3) * 3 * GRID_SIZE + MARGIN;
                    x = s_id * GRID_SIZE + MARGIN;
                }
            } else if (n.type === 'bridge') {
                // BRG_0_3 -> x from V0, y from H3
                let b_parts = n.id.split('_');
                if (b_parts.length == 3) {
                    let v = parseInt(b_parts[1]);
                    let h = parseInt(b_parts[2]);
                    x = v * 3 * GRID_SIZE + MARGIN + 40;
                    y = (h - 3) * 3 * GRID_SIZE + MARGIN + 40;
                }
            }

            nodePositions[n.id] = {x: x, y: y, type: n.type};
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        });

        canvas.width = maxX + MARGIN * 2;
        canvas.height = maxY + MARGIN * 2;
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const cycleData = traceData.cycles[currentCycleIdx];
        if (!cycleData) return;

        // 1. Draw Static Links
        ctx.strokeStyle = '#ccc';
        ctx.lineWidth = 2;
        traceData.topology.links.forEach(l => {
            const src = nodePositions[l.src];
            const dst = nodePositions[l.dst];
            if (src && dst) {
                ctx.beginPath();
                ctx.moveTo(src.x, src.y);
                ctx.lineTo(dst.x, dst.y);
                ctx.stroke();
            }
        });

        // 2. Draw Active Links (Flits on fly)
        ctx.strokeStyle = '#e74c3c';
        ctx.lineWidth = 4;
        cycleData.links.forEach(l => {
            if (l.occupied) {
                const src = nodePositions[l.src];
                const dst = nodePositions[l.dst];
                if (src && dst) {
                    // Draw a flit moving from src to dst (simplified as drawing the whole link red)
                    ctx.beginPath();
                    ctx.moveTo(src.x, src.y);
                    ctx.lineTo(dst.x, dst.y);
                    ctx.stroke();

                    // Draw flit ID
                    const mx = (src.x + dst.x) / 2;
                    const my = (src.y + dst.y) / 2;
                    ctx.fillStyle = 'black';
                    ctx.fillText("F"+l.flit_id, mx, my);
                }
            }
        });

        // 3. Draw Nodes
        traceData.topology.nodes.forEach(n => {
            const pos = nodePositions[n.id];
            if (!pos) return;

            ctx.beginPath();
            if (n.type === 'bridge') {
                ctx.arc(pos.x, pos.y, 15, 0, Math.PI * 2);
                ctx.fillStyle = '#f39c12';
            } else {
                ctx.rect(pos.x - 10, pos.y - 10, 20, 20);
                ctx.fillStyle = '#bdc3c7';
            }
            ctx.fill();
            ctx.stroke();

            // Draw name tiny
            ctx.fillStyle = '#333';
            ctx.font = '10px Arial';
            ctx.fillText(n.id, pos.x - 15, pos.y - 15);
        });

        // 4. Draw Buffer Occupancies
        cycleData.buffers.forEach(b => {
            const pos = nodePositions[b.node];
            if (pos && b.size > 0) {
                ctx.fillStyle = '#c0392b';
                ctx.beginPath();
                ctx.arc(pos.x + 15, pos.y - 15, 8, 0, Math.PI*2);
                ctx.fill();
                ctx.fillStyle = 'white';
                ctx.font = '10px Arial';
                ctx.fillText(b.size, pos.x + 12, pos.y - 12);
            }
        });

        // Update UI
        document.getElementById('lbl-cycle').innerText = cycleData.cycle;
        document.getElementById('cycle-slider').value = currentCycleIdx;
    }

    // Init
    document.getElementById('lbl-max-cycle').innerText = traceData.cycles.length - 1;
    document.getElementById('cycle-slider').max = traceData.cycles.length - 1;
    generateLayout();
    draw();

    // Controls
    document.getElementById('btn-prev').onclick = () => {
        if (currentCycleIdx > 0) currentCycleIdx--;
        draw();
    };

    document.getElementById('btn-next').onclick = () => {
        if (currentCycleIdx < traceData.cycles.length - 1) currentCycleIdx++;
        draw();
    };

    document.getElementById('cycle-slider').oninput = (e) => {
        currentCycleIdx = parseInt(e.target.value);
        draw();
    };

    document.getElementById('btn-play').onclick = () => {
        playing = !playing;
        if (playing) {
            playInterval = setInterval(() => {
                if (currentCycleIdx < traceData.cycles.length - 1) {
                    currentCycleIdx++;
                    draw();
                } else {
                    playing = false;
                    clearInterval(playInterval);
                }
            }, 500);
        } else {
            clearInterval(playInterval);
        }
    };

    // Interactive hover
    canvas.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        let found = false;
        for (let n of traceData.topology.nodes) {
            const pos = nodePositions[n.id];
            if (pos && Math.abs(mouseX - pos.x) < 20 && Math.abs(mouseY - pos.y) < 20) {
                found = true;

                let html = `<strong>${n.id}</strong> (${n.type})<br>`;
                const cycleData = traceData.cycles[currentCycleIdx];
                if (cycleData) {
                    const bufs = cycleData.buffers.filter(b => b.node === n.id);
                    if (bufs.length > 0) {
                        html += '<ul>';
                        bufs.forEach(b => {
                            html += `<li>${b.type}: ${b.size}/${b.capacity} (Flits: ${b.flits.join(',')})</li>`;
                        });
                        html += '</ul>';
                    } else {
                        html += '<p>No buffered flits.</p>';
                    }
                }
                document.getElementById('node-details').innerHTML = html;
                break;
            }
        }
        if (!found) {
            document.getElementById('node-details').innerHTML = "Hover over a node to see buffer status.";
        }
    });

</script>
</body>
</html>
"""

def generate():
    trace_path = "reports/huawei_c_model/ca_trace.json"
    out_path = "reports/huawei_c_model/ca_visualizer.html"

    if not os.path.exists(trace_path):
        print(f"Error: {trace_path} not found.")
        return

    with open(trace_path, 'r') as f:
        trace_json = f.read()

    html = HTML_TEMPLATE.replace("{TRACE_DATA}", trace_json)

    with open(out_path, 'w') as f:
        f.write(html)

    print(f"Visualizer generated at {out_path}")

if __name__ == "__main__":
    generate()
