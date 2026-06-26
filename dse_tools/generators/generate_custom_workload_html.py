import os
import json

def generate_html():
    results_file = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'custom_workload_results.json')
    if not os.path.exists(results_file):
        print(f"Error: {results_file} not found.")
        return

    with open(results_file, 'r') as f:
        results = json.load(f)

    # Convert results into JS-friendly variables
    js_data = "const dseResults = " + json.dumps(results) + ";"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-width=1.0">
    <title>NoC DSE: Custom Workload Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .header-panel {{ background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .header-panel h2 {{ margin-top: 0; color: #2980b9; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
        th {{ background-color: #34495e; color: white; }}
        .heatmap-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }}
        .topology-card {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; width: 400px; }}
        canvas {{ border: 1px solid #eee; border-radius: 4px; background-color: #fafafa; }}
        .tooltip {{
            position: absolute; background: rgba(0,0,0,0.8); color: white; padding: 5px 10px;
            border-radius: 4px; pointer-events: none; opacity: 0; transition: opacity 0.2s; font-size: 12px;
        }}
    </style>
</head>
<body>

    <h1>NoC 客製化流量端到端分析報告 (Custom Workload DSE)</h1>

    <div class="header-panel">
        <h2>環境與設定 (Environmental Settings)</h2>
        <p><strong>架構規模:</strong> 16 節點 (4x4 Mesh/Torus 或是 16-node Ring)</p>
        <p><strong>時脈頻率 (Frequency):</strong> 1.5 GHz</p>
        <p><strong>資料寬度 (Data Width):</strong> 64 Bytes / cycle</p>
        <p><strong>單一通道極限頻寬 (Link Max BW):</strong> 96 GB/sec</p>
        <p><strong>流量特徵:</strong> 依據使用者給定之非均勻 16x16 機率矩陣與獨立注入率 (BW Utilization)。部分節點要求 100% (96GB/s) 發送頻寬。</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>拓撲結構 (Topology)</th>
                <th>理論最大通道負載 (FLITs/cycle)</th>
                <th>C Model 吞吐量 (Packets/cycle)</th>
                <th>C Model 平均延遲 (Cycles)</th>
            </tr>
        </thead>
        <tbody id="table-body">
            <!-- Populated via JS -->
        </tbody>
    </table>

    <h2 style="text-align:center; color:#2c3e50;">理論熱點分佈圖 (Topology Heatmaps)</h2>
    <div class="heatmap-container" id="heatmap-container">
        <!-- Canvas generated via JS -->
    </div>

    <div id="tooltip" class="tooltip"></div>

    <script>
        {js_data}

        function populateTable() {{
            const tbody = document.getElementById('table-body');
            for (const [topo, data] of Object.entries(dseResults)) {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${{topo.toUpperCase()}}</strong></td>
                    <td>${{data.theory_max_load.toFixed(4)}}</td>
                    <td>${{data.c_model_throughput.toFixed(4)}}</td>
                    <td>${{data.c_model_latency.toFixed(2)}}</td>
                `;
                tbody.appendChild(tr);
            }}
        }}

        function drawHeatmaps() {{
            const container = document.getElementById('heatmap-container');
            for (const [topo, data] of Object.entries(dseResults)) {{
                const card = document.createElement('div');
                card.className = 'topology-card';
                card.innerHTML = `<h3>${{topo.toUpperCase()}} Topology</h3><canvas id="canvas-${{topo}}" width="350" height="350"></canvas>`;
                container.appendChild(card);

                const canvas = document.getElementById(`canvas-${{topo}}`);
                const ctx = canvas.getContext('2d');
                renderTopology(ctx, topo, data.theory_edge_loads, data.theory_max_load);
            }}
        }}

        function renderTopology(ctx, type, edgesData, maxLoad) {{
            const width = 350;
            const height = 350;
            const padding = 40;

            // Calculate coordinates for 16 nodes
            let coords = {{}};
            if (type === 'mesh' || type === 'torus') {{
                const cols = 4, rows = 4;
                const cellW = (width - 2*padding) / (cols - 1);
                const cellH = (height - 2*padding) / (rows - 1);
                for (let i = 0; i < 16; i++) {{
                    coords[i] = {{ x: padding + (i % cols) * cellW, y: padding + Math.floor(i / cols) * cellH }};
                }}
            }} else if (type === 'ring') {{
                const cx = width / 2;
                const cy = height / 2;
                const r = width / 2 - padding;
                for (let i = 0; i < 16; i++) {{
                    const angle = (i * 2 * Math.PI / 16) - Math.PI/2;
                    coords[i] = {{ x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }};
                }}
            }}

            // Draw Edges
            for (const [edgeStr, load] of Object.entries(edgesData)) {{
                if (load <= 0) continue;
                const [u, v] = edgeStr.split('->').map(Number);
                const p1 = coords[u];
                const p2 = coords[v];

                // Color based on load intensity
                const intensity = maxLoad > 0 ? load / maxLoad : 0;
                // Cold (Blue) to Hot (Red)
                const r = Math.floor(255 * intensity);
                const b = Math.floor(255 * (1 - intensity));
                ctx.strokeStyle = `rgb(${{r}}, 0, ${{b}})`;
                ctx.lineWidth = 1 + (intensity * 4);

                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }}

            // Draw Nodes
            for (let i = 0; i < 16; i++) {{
                const p = coords[i];
                ctx.fillStyle = '#fff';
                ctx.strokeStyle = '#333';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 10, 0, 2*Math.PI);
                ctx.fill();
                ctx.stroke();

                ctx.fillStyle = '#333';
                ctx.font = '10px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(i, p.x, p.y);
            }}
        }}

        window.onload = () => {{
            populateTable();
            drawHeatmaps();
        }};
    </script>
</body>
</html>
"""

    html_path = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'custom_workload_report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML Report generated at {html_path}")

if __name__ == "__main__":
    generate_html()
