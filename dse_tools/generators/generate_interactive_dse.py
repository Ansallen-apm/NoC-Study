import json
import os

def generate_interactive_html():
    json_path = 'dse_tools/report/verification_results.json'

    if not os.path.exists(json_path):
        print(f"Error: {json_path} does not exist.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取所有不重複的選項，包含新的參數
    topologies = sorted(list(set(d.get('topology') for d in data if d.get('topology'))))
    routings = sorted(list(set(d.get('routing') for d in data if d.get('routing'))))
    traffics = sorted(list(set(d.get('traffic', 'uniform') for d in data)))
    packet_sizes = sorted(list(set(d.get('packet_size', 1) for d in data)))
    buffer_sizes = sorted(list(set(d.get('buffer_size', 8) for d in data)))
    vcs = sorted(list(set(d.get('vcs', 1) for d in data)))

    options = {
        "topology": topologies,
        "routing": routings,
        "traffic": traffics,
        "packet_size": packet_sizes,
        "buffer_size": buffer_sizes,
        "vcs": vcs
    }

    # 準備供 Chart.js 使用的曲線資料
    chart_data = []
    for item in data:
        # 轉換 latency curve 格式給 Chart.js
        curve = []
        if 'latency_curve' in item:
            for pt in item['latency_curve']:
                if pt['latency'] != float('inf'):
                    curve.append({'x': pt['rate'], 'y': pt['latency']})

        entry = {
            "topology": item.get('topology'),
            "dim": item.get('dim'),
            "nodes": item.get('nodes'),
            "routing": item.get('routing'),
            "traffic": item.get('traffic', 'uniform'),
            "packet_size": item.get('packet_size', 1),
            "buffer_size": item.get('buffer_size', 8),
            "vcs": item.get('vcs', 1),
            "theory_avg_hops": item.get('theory_avg_hops', 0),
            "theory_max_rate": item.get('theory_max_rate', 0),
            "theory_max_load": item.get('theory_max_load', 0),
            "theory_bisection_bw": item.get('theory_bisection_bw', 0),
            "booksim_zero_load_lat": item.get('booksim_zero_load_lat', 0),
            "booksim_actual_sat_rate": item.get('booksim_actual_sat_rate', 0),
            "booksim_total_throughput": item.get('booksim_total_throughput', 0),
            "theory_edge_loads": item.get('theory_edge_loads', {}), # For Mode C JS drawing
            "curve": curve
        }
        chart_data.append(entry)

    options_json = json.dumps(options)
    chart_data_json = json.dumps(chart_data)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NoC DSE 互動式分析報告 (Interactive Report)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .controls {{ text-align: center; margin: 20px 0; }}
        select {{ padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #ccc; }}
        .chart-container {{ position: relative; height: 60vh; width: 100%; display: flex; justify-content: center; align-items: center; }}
        .btn-group {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; }}
        .btn {{ padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; color: white; font-weight: bold; font-size: 16px; }}
        canvas {{ max-width: 100%; max-height: 100%; }}
        #topologyCanvas {{ background-color: #fafafa; border: 1px solid #ddd; border-radius: 8px; }}
    </style>
</head>
<body>

<div class="container">
    <h1>🚀 網路晶片架構探索 (NoC DSE) 互動式分析報告</h1>

    <div class="btn-group">
        <button id="btnModeA" class="btn" style="background-color: #3cb44b;" onclick="setMode('A')">模式 A：效能曲線 (Latency Curves)</button>
        <button id="btnModeB" class="btn" style="background-color: #ccc;" onclick="setMode('B')">模式 B：特徵相關性 (Scatter Correlation)</button>
        <button id="btnModeC" class="btn" style="background-color: #ccc;" onclick="setMode('C')">模式 C：動態熱點圖 (Dynamic Heatmap)</button>
    </div>

    <!-- MODE A Controls -->
    <div id="modeAControls" class="controls">
        <label>Topology: <select id="topoSelect" onchange="updateChart()"></select></label>
        <label>Routing: <select id="rSelect" onchange="updateChart()"></select></label>
        <label>Traffic: <select id="tSelect" onchange="updateChart()"></select></label>
        <br><br>
        <label>Packet Size: <select id="pSelect" onchange="updateChart()"></select></label>
        <label>Buffer Size: <select id="bSelect" onchange="updateChart()"></select></label>
        <label>VCs: <select id="vSelect" onchange="updateChart()"></select></label>
        <br><br>
        <label>比較維度 (Compare By):
            <select id="compareSelect" onchange="updateChart()">
                <option value="dim">網路大小 (Nodes/Dimensions)</option>
                <option value="routing">路由演算法 (Routing)</option>
                <option value="traffic">流量模式 (Traffic)</option>
                <option value="packet_size">封包大小 (Packet Size)</option>
                <option value="buffer_size">緩衝區大小 (Buffer Size)</option>
                <option value="vcs">虛擬通道數 (VCs)</option>
            </select>
        </label>
    </div>

    <!-- MODE B Controls -->
    <div id="modeBControls" class="controls" style="display: none;">
        <label>X 軸 (X-Axis):
            <select id="scatterX" onchange="updateChart()">
                <option value="theory_avg_hops">理論平均跳數 (Theory Avg Hops)</option>
                <option value="theory_max_rate">理論最大注入率 (Theory Max Rate)</option>
                <option value="theory_max_load">理論最大通道負載 (Theory Max Load)</option>
                <option value="theory_bisection_bw">理論二分頻寬 (Theory Bisection BW)</option>
            </select>
        </label>
        <label>Y 軸 (Y-Axis):
            <select id="scatterY" onchange="updateChart()">
                <option value="booksim_zero_load_lat">實際零負載延遲 (Zero-Load Latency)</option>
                <option value="booksim_actual_sat_rate">實際飽和注入率 (Actual Sat Rate)</option>
                <option value="booksim_total_throughput">實際總吞吐量 (Total Throughput)</option>
            </select>
        </label>
    </div>

    <!-- MODE C Controls -->
    <div id="modeCControls" class="controls" style="display: none;">
        <label>Topology: <select id="topoSelectC" onchange="updateChart()"></select></label>
        <label>Dimension: <select id="dimSelectC" onchange="updateChart()"></select></label>
        <br><br>
        <span style="color: #666; font-size: 0.9em;">(動態 JavaScript 繪製，深紅色代表網路熱點瓶頸，淺藍色代表負載較低)</span>
    </div>

    <div class="chart-container">
        <!-- For Mode A and B -->
        <canvas id="dseChart"></canvas>
        <!-- For Mode C -->
        <canvas id="topologyCanvas" width="800" height="600" style="display: none;"></canvas>
    </div>
</div>

<script>
    const allData = {chart_data_json};
    const allOptions = {options_json};

    let currentMode = 'A';
    let myChart = null;

    function setMode(mode) {{
        currentMode = mode;
        document.getElementById('modeAControls').style.display = 'none';
        document.getElementById('modeBControls').style.display = 'none';
        document.getElementById('modeCControls').style.display = 'none';
        document.getElementById('btnModeA').style.backgroundColor = '#ccc';
        document.getElementById('btnModeB').style.backgroundColor = '#ccc';
        document.getElementById('btnModeC').style.backgroundColor = '#ccc';

        if (mode === 'A') {{
            document.getElementById('modeAControls').style.display = 'block';
            document.getElementById('btnModeA').style.backgroundColor = '#3cb44b';
        }} else if (mode === 'B') {{
            document.getElementById('modeBControls').style.display = 'block';
            document.getElementById('btnModeB').style.backgroundColor = '#4363d8';
        }} else if (mode === 'C') {{
            document.getElementById('modeCControls').style.display = 'block';
            document.getElementById('btnModeC').style.backgroundColor = '#f58231';
        }}
        updateChart();
    }}

    function populateSelect(id, optionsArray, addAllOption = true) {{
        const select = document.getElementById(id);
        select.innerHTML = '';
        if (addAllOption) {{
            select.add(new Option('全部 (All)', 'all'));
        }}
        optionsArray.forEach(opt => select.add(new Option(opt, opt)));
    }}

    // 幫定值到 0~1 的熱圖顏色函數 (藍 -> 綠 -> 黃 -> 紅)
    function valueToColor(val) {{
        val = Math.max(0, Math.min(1, val));
        // Simple Jet colormap approximation
        let r = Math.max(0, Math.min(255, Math.round(255 * (1.5 - Math.abs(1 - 4 * (val - 0.5))))));
        let g = Math.max(0, Math.min(255, Math.round(255 * (1.5 - Math.abs(1 - 4 * (val - 0.25))))));
        let b = Math.max(0, Math.min(255, Math.round(255 * (1.5 - Math.abs(1 - 4 * val)))));
        if (val < 0.25) {{ r = 0; g = Math.round(4 * val * 255); b = 255; }}
        else if (val < 0.5) {{ r = 0; g = 255; b = Math.round(255 * (1 - 4 * (val - 0.25))); }}
        else if (val < 0.75) {{ r = Math.round(255 * 4 * (val - 0.5)); g = 255; b = 0; }}
        else {{ r = 255; g = Math.round(255 * (1 - 4 * (val - 0.75))); b = 0; }}
        return `rgb(${{r}}, ${{g}}, ${{b}})`;
    }}

    function drawTopology(record) {{
        const canvas = document.getElementById('topologyCanvas');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!record || !record.theory_edge_loads || Object.keys(record.theory_edge_loads).length === 0) {{
            ctx.font = '20px sans-serif';
            ctx.fillStyle = '#000';
            ctx.fillText('無熱點資料可供繪製', 300, 300);
            return;
        }}

        const edgeLoads = record.theory_edge_loads;
        const topo = record.topology;
        const dim = parseInt(record.dim);

        // 將有向邊轉無向邊以繪製
        const undirectedLoads = {{}};
        let maxLoad = 1;
        for (const [key, load] of Object.entries(edgeLoads)) {{
            const parts = key.split('->');
            if (parts.length === 2) {{
                const u = parseInt(parts[0]);
                const v = parseInt(parts[1]);
                const edgeKey = u < v ? `${{u}}-${{v}}` : `${{v}}-${{u}}`;
                undirectedLoads[edgeKey] = (undirectedLoads[edgeKey] || 0) + load;
                if (undirectedLoads[edgeKey] > maxLoad) maxLoad = undirectedLoads[edgeKey];
            }}
        }}

        const margin = 50;
        const width = canvas.width - 2 * margin;
        const height = canvas.height - 2 * margin;

        // 計算節點位置
        const pos = {{}};
        if (topo === 'mesh' || topo === 'torus') {{
            const nodeSpacingX = width / (dim - 1 || 1);
            const nodeSpacingY = height / (dim - 1 || 1);
            for (let i = 0; i < record.nodes; i++) {{
                const x = i % dim;
                const y = Math.floor(i / dim);
                pos[i] = {{ x: margin + x * nodeSpacingX, y: margin + y * nodeSpacingY }};
            }}
        }} else if (topo === 'ring') {{
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;
            const r = Math.min(width, height) / 2;
            for (let i = 0; i < record.nodes; i++) {{
                const angle = i * (2 * Math.PI / record.nodes) - Math.PI / 2;
                pos[i] = {{ x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }};
            }}
        }}

        // 繪製邊
        for (const [key, load] of Object.entries(undirectedLoads)) {{
            const parts = key.split('-');
            const u = parseInt(parts[0]);
            const v = parseInt(parts[1]);

            if (pos[u] && pos[v]) {{
                const normalized = load / maxLoad;
                ctx.beginPath();
                ctx.moveTo(pos[u].x, pos[u].y);

                // 若為 Torus 的 wrap-around 邊界線，用弧線畫以免重疊
                if (topo === 'torus') {{
                    const ux = u % dim, uy = Math.floor(u / dim);
                    const vx = v % dim, vy = Math.floor(v / dim);
                    if (Math.abs(ux - vx) > 1 || Math.abs(uy - vy) > 1) {{
                        ctx.quadraticCurveTo(canvas.width/2, canvas.height/2, pos[v].x, pos[v].y);
                    }} else {{
                        ctx.lineTo(pos[v].x, pos[v].y);
                    }}
                }} else {{
                    ctx.lineTo(pos[v].x, pos[v].y);
                }}

                ctx.strokeStyle = valueToColor(normalized);
                ctx.lineWidth = 1 + 6 * normalized;
                ctx.stroke();
            }}
        }}

        // 繪製節點
        for (let i = 0; i < record.nodes; i++) {{
            if (pos[i]) {{
                ctx.beginPath();
                ctx.arc(pos[i].x, pos[i].y, 12, 0, 2 * Math.PI);
                ctx.fillStyle = '#fff';
                ctx.fill();
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#333';
                ctx.stroke();

                ctx.fillStyle = '#000';
                ctx.font = '10px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(i, pos[i].x, pos[i].y);
            }}
        }}

        // Draw Legend
        ctx.fillStyle = '#000';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`Max Load: ${{maxLoad}}`, 10, 20);
    }}

    function updateChart() {{
        const canvasA = document.getElementById('dseChart');
        const canvasC = document.getElementById('topologyCanvas');

        if (myChart) myChart.destroy();

        if (currentMode === 'A' || currentMode === 'B') {{
            canvasA.style.display = 'block';
            canvasC.style.display = 'none';
            const ctx = canvasA.getContext('2d');
            const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0'];

            if (currentMode === 'A') {{
                const topo = document.getElementById('topoSelect').value;
                const routing = document.getElementById('rSelect').value;
                const traffic = document.getElementById('tSelect').value;
                const pSize = document.getElementById('pSelect').value;
                const bSize = document.getElementById('bSelect').value;
                const vcs = document.getElementById('vSelect').value;
                const compareBy = document.getElementById('compareSelect').value;

                let filteredData = allData.filter(d => d.topology === topo);

                if (compareBy !== 'routing' && routing !== 'all') filteredData = filteredData.filter(d => d.routing === routing);
                if (compareBy !== 'traffic' && traffic !== 'all') filteredData = filteredData.filter(d => d.traffic === traffic);
                if (compareBy !== 'packet_size' && pSize !== 'all') filteredData = filteredData.filter(d => d.packet_size == parseInt(pSize));
                if (compareBy !== 'buffer_size' && bSize !== 'all') filteredData = filteredData.filter(d => d.buffer_size == parseInt(bSize));
                if (compareBy !== 'vcs' && vcs !== 'all') filteredData = filteredData.filter(d => d.vcs == parseInt(vcs));

                if (compareBy !== 'dim') {{
                    if (filteredData.length > 0) {{
                        const maxNodes = Math.max(...filteredData.map(d => d.nodes));
                        filteredData = filteredData.filter(d => d.nodes === maxNodes);
                    }}
                }}

                let datasets = [];
                filteredData.forEach((d, i) => {{
                    if (d.curve.length > 0) {{
                        let label = `Nodes: ${{d.nodes}}`;
                        if (compareBy === 'routing') label = `Routing: ${{d.routing}} (Nodes: ${{d.nodes}})`;
                        if (compareBy === 'traffic') label = `Traffic: ${{d.traffic}} (Nodes: ${{d.nodes}})`;
                        if (compareBy === 'packet_size') label = `Packet: ${{d.packet_size}} flits (Nodes: ${{d.nodes}})`;
                        if (compareBy === 'buffer_size') label = `Buffer: ${{d.buffer_size}} flits (Nodes: ${{d.nodes}})`;
                        if (compareBy === 'vcs') label = `VCs: ${{d.vcs}} (Nodes: ${{d.nodes}})`;
                        if (compareBy === 'dim') label = `Nodes: ${{d.nodes}} (R:${{d.routing}}, P:${{d.packet_size}}, B:${{d.buffer_size}}, V:${{d.vcs}})`;

                        datasets.push({{
                            label: label,
                            data: d.curve,
                            borderColor: colors[i % colors.length],
                            backgroundColor: colors[i % colors.length],
                            fill: false,
                            tension: 0.1,
                            pointRadius: 5,
                            pointHoverRadius: 8
                        }});
                    }}
                }});

                myChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{ datasets: datasets }},
                    options: {{
                        responsive: true, maintainAspectRatio: false,
                        scales: {{ x: {{ type: 'linear', title: {{ display: true, text: 'Injection Rate' }} }}, y: {{ title: {{ display: true, text: 'Latency' }} }} }}
                    }}
                }});
            }} else if (currentMode === 'B') {{
                const xKey = document.getElementById('scatterX').value;
                const yKey = document.getElementById('scatterY').value;

                // 為了比較理論極限，Mode B 我們過濾出 packet=1, buffer=8 的結果
                const baseData = allData.filter(d => d.packet_size === 1 && d.buffer_size === 8 && d.theory_avg_hops > 0);

                const topos = ['mesh', 'torus', 'ring'];
                let datasets = [];

                topos.forEach((topo, index) => {{
                    let pts = [];
                    baseData.filter(d => d.topology === topo).forEach(d => {{
                        let xVal = d[xKey];
                        let yVal = d[yKey];
                        if (xVal !== undefined && yVal !== undefined && xVal !== null && yVal !== null && xVal !== Infinity && yVal !== Infinity) {{
                            pts.push({{ x: xVal, y: yVal, _meta: `Nodes: ${{d.nodes}}` }});
                        }}
                    }});
                    if (pts.length > 0) {{
                        datasets.push({{
                            label: topo.toUpperCase(),
                            data: pts,
                            backgroundColor: colors[index % colors.length],
                            pointRadius: 8,
                            pointHoverRadius: 12
                        }});
                    }}
                }});

                myChart = new Chart(ctx, {{
                    type: 'scatter',
                    data: {{ datasets: datasets }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            tooltip: {{ callbacks: {{ label: function(context) {{ return context.dataset.label + ' ' + context.raw._meta + ' | X: ' + context.parsed.x + ', Y: ' + context.parsed.y; }} }} }},
                            legend: {{ position: 'right' }}
                        }},
                        scales: {{
                            x: {{ title: {{ display: true, text: document.getElementById('scatterX').options[document.getElementById('scatterX').selectedIndex].text, font: {{ size: 14, weight: 'bold' }} }} }},
                            y: {{ title: {{ display: true, text: document.getElementById('scatterY').options[document.getElementById('scatterY').selectedIndex].text, font: {{ size: 14, weight: 'bold' }} }} }}
                        }}
                    }}
                }});
            }}
        }} else if (currentMode === 'C') {{
            canvasA.style.display = 'none';
            canvasC.style.display = 'block';

            const topo = document.getElementById('topoSelectC').value;
            const dim = parseInt(document.getElementById('dimSelectC').value);

            let record = allData.find(d => d.topology === topo && parseInt(d.dim) === dim && d.theory_edge_loads && Object.keys(d.theory_edge_loads).length > 0);
            drawTopology(record);
        }}
    }}

    window.onload = function() {{
        let dims = [...new Set(allData.map(d => d.dim))].sort((a,b) => a-b);
        populateSelect('topoSelect', allOptions.topology, false);
        populateSelect('rSelect', allOptions.routing, true);
        populateSelect('tSelect', allOptions.traffic, true);
        populateSelect('pSelect', allOptions.packet_size, true);
        populateSelect('bSelect', allOptions.buffer_size, true);
        populateSelect('vSelect', allOptions.vcs, true);
        populateSelect('topoSelectC', allOptions.topology, false);
        populateSelect('dimSelectC', dims, false);
        updateChart();
    }};
</script>
</body>
</html>
"""
    output_path = "dse_tools/report/interactive_dse_trends.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"互動式 HTML 報告已產生：{output_path}")

if __name__ == "__main__":
    generate_interactive_html()
