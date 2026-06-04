import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os

def generate_interactive_html():
    unified_data = []

    # 1. 讀取 verification_results.json (主要是 Mesh/Torus/Ring 固定參數的掃描)
    if os.path.exists('dse_tools/report/verification_results.json'):
        with open('dse_tools/report/verification_results.json', 'r', encoding='utf-8') as f:
            v_results = json.load(f)
            for r in v_results:
                vcs = r.get('vcs') if 'vcs' in r else (1 if r['topology'] == 'mesh' else 2)
                routing = r.get('routing', 'xy' if r['topology'] == 'mesh' else 'dim_order')
                traffic = r.get('traffic', 'uniform')
                record = {
                    "topology": r['topology'],
                    "dim": r['dim'],
                    "nodes": r['nodes'],
                    "routing": routing,
                    "traffic": traffic,
                    "packet_size": 1,
                    "buffer_size": 8,
                    "vcs": vcs,
                    "theory_channel_count": r.get('theory_channel_count', 0),
                    "theory_bisection_bw": r.get('theory_bisection_bw', 0),
                    "theory_max_load": r.get('theory_max_load', 0),
                    "theory_edge_loads": r.get('theory_edge_loads', {}),
                    "theory_avg_hops": r.get('theory_avg_hops', 0),
                    "theory_max_rate": r.get('theory_max_rate', 0),
                    "booksim_zero_load_lat": r.get('booksim_zero_load_lat', 0),
                    "booksim_actual_sat_rate": r.get('booksim_actual_sat_rate', 0),
                    "booksim_total_throughput": r.get('booksim_total_throughput', 0),
                    "curve": [ {"x": pt['rate'], "y": pt['latency']} for pt in r.get('latency_curve', []) if pt['latency'] != float('inf') ]
                }
                if record["curve"]:
                    unified_data.append(record)

    # 2. 讀取 report_full_booksim_ring.json (Ring 拓撲的龐大參數矩陣掃描)
    if os.path.exists('dse_tools/report/report_full_booksim_ring.json'):
        with open('dse_tools/report/report_full_booksim_ring.json', 'r', encoding='utf-8') as f:
            r_results = json.load(f)
            for key, runs in r_results.items():
                dim = int(key.split('_')[1])
                # 因為這份資料是離散點，我們需要把它依照相同的組合聚集成曲線
                grouped_runs = {}
                for run in runs:
                    if run.get('latency', float('inf')) == float('inf'):
                        continue

                    routing = run.get('routing', 'dim_order')
                    traffic = run.get('traffic', 'uniform')

                    group_key = (routing, traffic, run['packet_size'], run['buffer_size'], run['num_vcs'])
                    if group_key not in grouped_runs:
                        grouped_runs[group_key] = []
                    grouped_runs[group_key].append({"x": run['injection_rate'], "y": run['latency']})

                for (rt, tr, p, b, v), points in grouped_runs.items():
                    # 排序點位，確保畫線正確
                    points.sort(key=lambda pt: pt['x'])
                    record = {
                        "topology": "ring",
                        "dim": dim,
                        "nodes": dim, # 對 Ring 來說 dim 即為 nodes
                        "routing": rt,
                        "traffic": tr,
                        "packet_size": p,
                        "buffer_size": b,
                        "vcs": v,
                        "curve": points
                    }
                    unified_data.append(record)

    # 動態產生所有可選的參數列表
    options = {
        "topology": sorted(list(set(r['topology'] for r in unified_data))),
        "routing": sorted(list(set(r['routing'] for r in unified_data))),
        "traffic": sorted(list(set(r['traffic'] for r in unified_data))),
        "packet_size": sorted(list(set(r['packet_size'] for r in unified_data))),
        "buffer_size": sorted(list(set(r['buffer_size'] for r in unified_data))),
        "vcs": sorted(list(set(r['vcs'] for r in unified_data)))
    }

    # 將 Python dict 轉為 JSON string 嵌入 HTML
    chart_data_json = json.dumps(unified_data)
    options_json = json.dumps(options)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>互動式 DSE 效能趨勢報告</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ color: #2c3e50; text-align: center; }}
            .controls {{ text-align: center; margin: 20px 0; }}
            select {{ padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #ccc; }}
            .chart-container {{ position: relative; height: 60vh; width: 100%; }}
        </style>
    </head>
    <body>

    <div class="container">
        <h1>互動式 NoC DSE 效能趨勢 (Latency vs. Load)</h1>

        <div class="controls" style="margin-bottom: 10px;">
            <button onclick="setMode('A')" id="btnModeA" style="padding: 10px 20px; font-weight: bold; background-color: #3cb44b; color: white; border: none; border-radius: 5px; cursor: pointer;">模式 A: 效能動態曲線 (Latency Curves)</button>
            <button onclick="setMode('B')" id="btnModeB" style="padding: 10px 20px; font-weight: bold; background-color: #ccc; color: white; border: none; border-radius: 5px; cursor: pointer;">模式 B: 架構交叉比對 (Scatter Plot)</button>
            <button onclick="setMode('C')" id="btnModeC" style="padding: 10px 20px; font-weight: bold; background-color: #ccc; color: white; border: none; border-radius: 5px; cursor: pointer;">模式 C: 通道負載分佈 (Channel Load Bar)</button>
        </div>

        <div id="modeAControls" class="controls">
            <fieldset style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>過濾器 (Filters)</strong></legend>

                <label>拓撲 (Topology): </label>
                <select id="topoSelect" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>路由 (Routing): </label>
                <select id="rSelect" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>流量 (Traffic): </label>
                <select id="tSelect" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>封包長度 (Packet Size): </label>
                <select id="pSelect" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>緩衝區 (Buffer Size): </label>
                <select id="bSelect" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>虛擬通道 (VCs): </label>
                <select id="vSelect" onchange="updateChart()"></select>
            </fieldset>
            <br><br>
            <fieldset style="border: 1px solid #3cb44b; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>比較維度 (Compare By)</strong></legend>
                <label>將以下維度展開為不同的曲線: </label>
                <select id="compareSelect" onchange="updateChart()">
                    <option value="dim" selected>節點數量 (Dimension/Nodes)</option>
                    <option value="routing">路由演算法 (Routing Algorithm)</option>
                    <option value="traffic">流量模式 (Traffic Pattern)</option>
                    <option value="packet_size">封包長度 (Packet Size)</option>
                    <option value="buffer_size">緩衝區大小 (Buffer Size)</option>
                    <option value="vcs">虛擬通道數 (VCs)</option>
                </select>
            </fieldset>
        </div>

        <div id="modeBControls" class="controls" style="display: none;">
            <fieldset style="border: 1px solid #4363d8; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>散佈圖維度設定 (Scatter Plot Axes)</strong></legend>

                <label>X 軸 (X-Axis): </label>
                <select id="scatterX" onchange="updateChart()">
                    <option value="nodes">節點數 (Nodes)</option>
                    <option value="theory_avg_hops">理論平均跳數 (Avg Hops)</option>
                    <option value="theory_max_load">最大通道負載 (Max Load)</option>
                    <option value="theory_bisection_bw">二分頻寬 (Bisection BW)</option>
                    <option value="theory_max_rate">理論最大注入率 (Max Rate)</option>
                    <option value="booksim_zero_load_lat">BookSim 零負載延遲 (Zero-Load Latency)</option>
                    <option value="booksim_actual_sat_rate">BookSim 實際飽和點 (Saturation Rate)</option>
                    <option value="booksim_total_throughput">BookSim 總吞吐量 (Total Throughput)</option>
                </select>
                &nbsp;&nbsp;&nbsp;&nbsp;

                <label>Y 軸 (Y-Axis): </label>
                <select id="scatterY" onchange="updateChart()">
                    <option value="booksim_zero_load_lat" selected>BookSim 零負載延遲 (Zero-Load Latency)</option>
                    <option value="nodes">節點數 (Nodes)</option>
                    <option value="theory_avg_hops">理論平均跳數 (Avg Hops)</option>
                    <option value="theory_max_load">最大通道負載 (Max Load)</option>
                    <option value="theory_bisection_bw">二分頻寬 (Bisection BW)</option>
                    <option value="theory_max_rate">理論最大注入率 (Max Rate)</option>
                    <option value="booksim_actual_sat_rate">BookSim 實際飽和點 (Saturation Rate)</option>
                    <option value="booksim_total_throughput">BookSim 總吞吐量 (Total Throughput)</option>
                </select>
            </fieldset>
            <br><br>
            <span style="color: #666; font-size: 0.9em;">提示：在 Mode B 中，我們只繪製具有完整架構參數分析的資料點 (P=1, B=8)。</span>
        </div>

        <div id="modeCControls" class="controls" style="display: none;">
            <fieldset style="border: 1px solid #f58231; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>選擇觀察拓撲 (Select Topology to Inspect Hotspots)</strong></legend>

                <label>拓撲 (Topology): </label>
                <select id="topoSelectC" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>節點維度 (Dimension): </label>
                <select id="dimSelectC" onchange="updateChart()"></select>
            </fieldset>
            <br><br>
            <span style="color: #666; font-size: 0.9em;">提示：Mode C 會顯示該拓撲下所有通道的熱點分佈圖 (Heatmap)。紅色代表高負載，藍色代表低負載。</span>
        </div>

        <div class="chart-container" id="chartContainer">
            <canvas id="dseChart"></canvas>
            <div id="heatmapContainer" style="display: none; width: 100%; height: 100%; position: relative;">
                <canvas id="heatmapCanvas" style="width: 100%; height: 100%;"></canvas>
                <div id="heatmapTooltip" style="position: absolute; display: none; background: rgba(0,0,0,0.8); color: white; padding: 5px 10px; border-radius: 4px; pointer-events: none; font-size: 14px; z-index: 10;"></div>
            </div>
        </div>
    </div>

    <script>
        // 來自 Python 的完整 DSE 曲線資料與選項
        const allData = {chart_data_json};
        const allOptions = {options_json};

        let currentMode = 'A';
        let heatmapNodes = [];
        let heatmapEdges = [];

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

        // 初始化下拉選單
        function populateSelect(id, optionsArray, addAllOption = true) {{
            const select = document.getElementById(id);
            if (addAllOption) {{
                let opt = document.createElement('option');
                opt.value = 'all';
                opt.text = '全部 (All)';
                select.add(opt);
            }}
            optionsArray.forEach(val => {{
                let opt = document.createElement('option');
                opt.value = val;
                opt.text = val;
                select.add(opt);
            }});
        }}

        // 預設顏色庫
        const colors = [
            '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
            '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'
        ];

        let myChart = null;

        function updateChart() {{
            const ctx = document.getElementById('dseChart').getContext('2d');
            if (myChart) {{
                myChart.destroy();
            }}

            // 預設隱藏 heatmap, 顯示 canvas
            document.getElementById('heatmapContainer').style.display = 'none';
            document.getElementById('dseChart').style.display = 'block';

            if (currentMode === 'A') {{
                // ===== MODE A: Latency Curves =====
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
                filteredData.forEach((d, index) => {{
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
                        borderColor: colors[index % colors.length],
                        backgroundColor: colors[index % colors.length],
                        fill: false,
                        tension: 0.1,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }});
                }});

                if (datasets.length === 0) datasets = [{{ label: '無符合資料 (No Data)', data: [] }}];

                myChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{ datasets: datasets }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            x: {{
                                type: 'linear',
                                title: {{ display: true, text: '注入率 (Injection Rate) [flits/node/cycle]', font: {{ size: 14, weight: 'bold' }} }},
                                min: 0
                            }},
                            y: {{
                                title: {{ display: true, text: '平均延遲 (Average Latency) [cycles]', font: {{ size: 14, weight: 'bold' }} }},
                                min: 0,
                                suggestedMax: 100
                            }}
                        }},
                        plugins: {{
                            tooltip: {{ callbacks: {{ label: function(context) {{ return context.dataset.label + ': Rate ' + context.parsed.x + ' -> Latency ' + context.parsed.y + ' cycles'; }} }} }},
                            legend: {{ position: 'right' }}
                        }}
                    }}
                }});

            }} else if (currentMode === 'B') {{
                // ===== MODE B: Scatter Plot =====
                const xKey = document.getElementById('scatterX').value;
                const yKey = document.getElementById('scatterY').value;

                // 為了比較理論極限，Mode B 我們過濾出 packet=1, buffer=8 的結果 (與 verification script 一致)
                const baseData = allData.filter(d => d.packet_size === 1 && d.buffer_size === 8 && d.theory_avg_hops > 0);

                // 把拓撲分開成不同的 dataset
                const topos = ['mesh', 'torus', 'ring'];
                let datasets = [];

                topos.forEach((topo, index) => {{
                    let topoData = baseData.filter(d => d.topology === topo);
                    let points = [];
                    topoData.forEach(d => {{
                        let xVal = d[xKey];
                        let yVal = d[yKey];
                        // 過濾不合法數值
                        if(xVal !== undefined && yVal !== undefined && xVal !== null && yVal !== null && xVal !== Infinity && yVal !== Infinity) {{
                            points.push({{ x: xVal, y: yVal, _meta: `Nodes: ${{d.nodes}}` }});
                        }}
                    }});

                    if(points.length > 0) {{
                        datasets.push({{
                            label: topo.toUpperCase(),
                            data: points,
                            backgroundColor: colors[index % colors.length],
                            pointRadius: 8,
                            pointHoverRadius: 12
                        }});
                    }}
                }});

                if (datasets.length === 0) datasets = [{{ label: '無符合資料 (No Data)', data: [] }}];

                myChart = new Chart(ctx, {{
                    type: 'scatter',
                    data: {{ datasets: datasets }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            x: {{
                                type: 'linear',
                                title: {{ display: true, text: document.getElementById('scatterX').options[document.getElementById('scatterX').selectedIndex].text, font: {{ size: 14, weight: 'bold' }} }}
                            }},
                            y: {{
                                title: {{ display: true, text: document.getElementById('scatterY').options[document.getElementById('scatterY').selectedIndex].text, font: {{ size: 14, weight: 'bold' }} }}
                            }}
                        }},
                        plugins: {{
                            tooltip: {{ callbacks: {{ label: function(context) {{ return context.dataset.label + ' ' + context.raw._meta + ' | X: ' + context.parsed.x + ', Y: ' + context.parsed.y; }} }} }},
                            legend: {{ position: 'right' }}
                        }}
                    }}
                }});
            }} else if (currentMode === 'C') {{
                // ===== MODE C: JS Canvas Heatmap =====
                document.getElementById('dseChart').style.display = 'none';
                document.getElementById('heatmapContainer').style.display = 'block';

                const topo = document.getElementById('topoSelectC').value;
                const dim = parseInt(document.getElementById('dimSelectC').value);

                // Find the relevant data record to get edge loads
                let targetData = null;
                for (let i = 0; i < allData.length; i++) {{
                    if (allData[i].topology === topo && allData[i].dim === dim && allData[i].theory_edge_loads) {{
                        targetData = allData[i];
                        break;
                    }}
                }}

                drawHeatmap(topo, dim, targetData ? targetData.theory_edge_loads : {{}});
            }}
        }}

        function getColorForLoad(load, maxLoad) {{
            if (maxLoad === 0 || load === 0) return 'rgba(200, 200, 200, 0.5)'; // Grey for zero load
            // Color scale from blue (low) to red (high)
            const ratio = load / maxLoad;
            const hue = (1 - ratio) * 240; // 240 is blue, 0 is red
            return `hsla(${{hue}}, 100%, 50%, 0.8)`;
        }}

        function drawHeatmap(topo, dim, edgeLoads) {{
            const canvas = document.getElementById('heatmapCanvas');
            const container = document.getElementById('heatmapContainer');
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            heatmapNodes = [];
            heatmapEdges = [];

            if (!edgeLoads || Object.keys(edgeLoads).length === 0) {{
                ctx.fillStyle = 'black';
                ctx.font = '20px Arial';
                ctx.fillText("尚無該拓撲的通道負載資料 (No edge load data available)", 50, 50);
                return;
            }}

            // Combine directional edge loads into undirected loads
            let undirectedLoads = {{}};
            for (let key in edgeLoads) {{
                const parts = key.split('->');
                if (parts.length === 2) {{
                    const u = parseInt(parts[0]);
                    const v = parseInt(parts[1]);
                    const minNode = Math.min(u, v);
                    const maxNode = Math.max(u, v);
                    const edgeKey = minNode + '-' + maxNode;
                    if (!undirectedLoads[edgeKey]) {{
                        undirectedLoads[edgeKey] = 0;
                    }}
                    undirectedLoads[edgeKey] += edgeLoads[key];
                }}
            }}

            let maxLoad = 0;
            for (let key in undirectedLoads) {{
                if (undirectedLoads[key] > maxLoad) maxLoad = undirectedLoads[key];
            }}

            const padding = 50;
            const drawWidth = canvas.width - padding * 2;
            const drawHeight = canvas.height - padding * 2;

            let nodes = [];
            let width = dim;
            let height = dim;

            if (topo === 'ring') {{
                width = dim;
                height = 1;
                const radius = Math.min(drawWidth, drawHeight) / 2;
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                for (let i = 0; i < dim; i++) {{
                    const angle = (i / dim) * 2 * Math.PI - Math.PI / 2;
                    nodes.push({{
                        id: i,
                        x: centerX + radius * Math.cos(angle),
                        y: centerY + radius * Math.sin(angle)
                    }});
                }}
            }} else {{ // mesh or torus
                const stepX = drawWidth / (width > 1 ? width - 1 : 1);
                const stepY = drawHeight / (height > 1 ? height - 1 : 1);
                for (let y = 0; y < height; y++) {{
                    for (let x = 0; x < width; x++) {{
                        nodes.push({{
                            id: y * width + x,
                            x: padding + x * stepX,
                            y: padding + y * stepY
                        }});
                    }}
                }}
            }}

            heatmapNodes = nodes;

            // Prepare edges based on undirectedLoads keys (e.g., "0-1")
            for (let key in undirectedLoads) {{
                const parts = key.split('-');
                if (parts.length === 2) {{
                    const u = parseInt(parts[0]);
                    const v = parseInt(parts[1]);
                    const load = undirectedLoads[key];
                    const nodeU = nodes.find(n => n.id === u);
                    const nodeV = nodes.find(n => n.id === v);

                    if (nodeU && nodeV) {{
                        let isWrapAround = false;
                        if (topo === 'torus' && (Math.abs(nodeU.x - nodeV.x) > drawWidth * 0.8 || Math.abs(nodeU.y - nodeV.y) > drawHeight * 0.8)) {{
                            isWrapAround = true;
                        }}

                        heatmapEdges.push({{
                            u: u, v: v,
                            x1: nodeU.x, y1: nodeU.y,
                            x2: nodeV.x, y2: nodeV.y,
                            load: load,
                            color: getColorForLoad(load, maxLoad),
                            isWrapAround: isWrapAround
                        }});
                    }}
                }}
            }}

            // Draw edges
            ctx.lineWidth = 4;
            for (let edge of heatmapEdges) {{
                ctx.beginPath();

                // For Torus wrap-around, draw curved or broken lines if distance is too large
                if (edge.isWrapAround) {{
                    ctx.strokeStyle = edge.color;
                    ctx.setLineDash([5, 5]); // dashed line for wrap-around

                    // Instead of Bezier crossing the center, draw straight lines going outwards
                    let midX1 = edge.x1;
                    let midY1 = edge.y1;
                    let midX2 = edge.x2;
                    let midY2 = edge.y2;

                    const extend = 40; // extend outwards

                    if (Math.abs(edge.x1 - edge.x2) > drawWidth * 0.8) {{
                        // Horizontal wrap-around
                        midX1 = edge.x1 > edge.x2 ? edge.x1 + extend : edge.x1 - extend;
                        midX2 = edge.x2 > edge.x1 ? edge.x2 + extend : edge.x2 - extend;
                    }}
                    if (Math.abs(edge.y1 - edge.y2) > drawHeight * 0.8) {{
                        // Vertical wrap-around
                        midY1 = edge.y1 > edge.y2 ? edge.y1 + extend : edge.y1 - extend;
                        midY2 = edge.y2 > edge.y1 ? edge.y2 + extend : edge.y2 - extend;
                    }}

                    ctx.moveTo(edge.x1, edge.y1);
                    ctx.lineTo(midX1, midY1);
                    ctx.moveTo(edge.x2, edge.y2);
                    ctx.lineTo(midX2, midY2);

                    // Save midpoints for hover detection
                    edge.mid1 = {{x: midX1, y: midY1}};
                    edge.mid2 = {{x: midX2, y: midY2}};

                }} else {{
                    ctx.moveTo(edge.x1, edge.y1);
                    ctx.strokeStyle = edge.color;
                    ctx.setLineDash([]);
                    ctx.lineTo(edge.x2, edge.y2);
                }}

                ctx.stroke();
            }}
            ctx.setLineDash([]); // reset

            // Draw nodes
            for (let node of nodes) {{
                ctx.beginPath();
                ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
                ctx.fillStyle = '#333';
                ctx.fill();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.stroke();
            }}
        }}

        function pointLineDistance(px, py, x1, y1, x2, y2) {{
            const A = px - x1;
            const B = py - y1;
            const C = x2 - x1;
            const D = y2 - y1;

            const dot = A * C + B * D;
            const len_sq = C * C + D * D;
            let param = -1;
            if (len_sq != 0)
                param = dot / len_sq;

            let xx, yy;

            if (param < 0) {{
                xx = x1;
                yy = y1;
            }}
            else if (param > 1) {{
                xx = x2;
                yy = y2;
            }}
            else {{
                xx = x1 + param * C;
                yy = y1 + param * D;
            }}

            const dx = px - xx;
            const dy = py - yy;
            return Math.sqrt(dx * dx + dy * dy);
        }}

        // Add mousemove listener for tooltip
        document.getElementById('heatmapCanvas').addEventListener('mousemove', function(e) {{
            if (currentMode !== 'C') return;
            const rect = this.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            let hoveredEdge = null;
            // Check edges (simple line distance)
            for (let edge of heatmapEdges) {{
                let distance = 9999;
                if (edge.isWrapAround) {{
                    // Check against the two segments extending outwards
                    const dist1 = pointLineDistance(mouseX, mouseY, edge.x1, edge.y1, edge.mid1.x, edge.mid1.y);
                    const dist2 = pointLineDistance(mouseX, mouseY, edge.x2, edge.y2, edge.mid2.x, edge.mid2.y);
                    distance = Math.min(dist1, dist2);
                }} else {{
                    distance = pointLineDistance(mouseX, mouseY, edge.x1, edge.y1, edge.x2, edge.y2);
                }}

                if (distance < 5) {{ // 5px tolerance
                    hoveredEdge = edge;
                    break;
                }}
            }}

            const tooltip = document.getElementById('heatmapTooltip');
            if (hoveredEdge) {{
                tooltip.style.display = 'block';
                tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
                tooltip.style.top = (e.clientY - rect.top + 15) + 'px';
                tooltip.innerHTML = `連線 (Edge): ${{hoveredEdge.u}} &rarr; ${{hoveredEdge.v}}<br>負載 (Load): ${{hoveredEdge.load}}`;
                this.style.cursor = 'pointer';
            }} else {{
                tooltip.style.display = 'none';
                this.style.cursor = 'default';
            }}
        }});

        // 初始化
        window.onload = function() {{
            // Extract unique dimensions for Mode C
            let dims = [...new Set(allData.map(item => item.dim))].sort((a,b) => a-b);

            // 填入下拉選項 (Topology 不給 All)
            populateSelect('topoSelect', allOptions.topology, false);
            populateSelect('rSelect', allOptions.routing, true);
            populateSelect('tSelect', allOptions.traffic, true);
            populateSelect('pSelect', allOptions.packet_size, true);
            populateSelect('bSelect', allOptions.buffer_size, true);
            populateSelect('vSelect', allOptions.vcs, true);

            populateSelect('topoSelectC', allOptions.topology, false);
            populateSelect('dimSelectC', dims, false);

            // 設定預設選項並更新
            if(allOptions.topology.includes('ring')) {{
                document.getElementById('topoSelect').value = 'ring';
                document.getElementById('topoSelectC').value = 'ring';
            }}
            updateChart();
        }};
    </script>
    </body>
    </html>
    """

    output_path = 'dse_tools/report/interactive_dse_trends.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"互動式 HTML 報告已產生：{output_path}")

if __name__ == "__main__":
    generate_interactive_html()
