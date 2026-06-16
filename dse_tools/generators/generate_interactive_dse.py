import sys
import os
import json
import os

def generate_interactive_html():
    unified_data = []

    # 1. 讀取 verification_results.json (主要是 Mesh/Torus/Ring 固定參數的掃描)
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "verification_results.json")):
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "verification_results.json"), 'r', encoding='utf-8') as f:
                v_results = json.load(f)
        except Exception as e:
            print(f"錯誤：讀取 verification_results.json 失敗 ({e})。")
            v_results = []

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
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "report_full_booksim_ring.json")):
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "report_full_booksim_ring.json"), 'r', encoding='utf-8') as f:
                r_results = json.load(f)
        except Exception as e:
            print(f"錯誤：讀取 report_full_booksim_ring.json 失敗 ({e})。")
            r_results = {}

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
            <button onclick="setMode('D')" id="btnModeD" style="padding: 10px 20px; font-weight: bold; background-color: #ccc; color: white; border: none; border-radius: 5px; cursor: pointer;">模式 D: 成本與效能權衡 (Pareto Plot)</button>
            <button onclick="setMode('E')" id="btnModeE" style="padding: 10px 20px; font-weight: bold; background-color: #ccc; color: white; border: none; border-radius: 5px; cursor: pointer;">模式 E: 極限壓力測試 (Radar Chart)</button>
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

                <br><br>
                <label><input type="checkbox" id="keepCurves" onchange="updateChart()"> 保留歷史曲線 (Keep Previous Curves)</label>
                &nbsp;&nbsp;
                <button onclick="clearHistory()" style="padding: 5px 10px; background-color: #f44336; color: white; border: none; border-radius: 3px; cursor: pointer;">清除歷史曲線 (Clear)</button>
            </fieldset>
        </div>

        <div id="modeBControls" class="controls" style="display: none;">
            <fieldset style="border: 1px solid #4363d8; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>散佈圖維度設定 (Scatter Plot Axes & Filters)</strong></legend>

                <label>封包長度 (Packet Size): </label>
                <select id="pSelectB" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>緩衝區大小 (Buffer Size): </label>
                <select id="bSelectB" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>虛擬通道數 (VCs): </label>
                <select id="vSelectB" onchange="updateChart()"></select>

                <br><br>
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
            <span style="color: #666; font-size: 0.9em;">提示：Mode B 可以透過上方過濾器選擇不同硬體配置下的拓撲效能分佈。</span>
        </div>

        <div id="modeCControls" class="controls" style="display: none;">
            <fieldset style="border: 1px solid #f58231; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>選擇觀察拓撲 (Select Topology to Inspect Hotspots)</strong></legend>

                <label>拓撲 (Topology): </label>
                <select id="topoSelectC" onchange="updateChart()"></select>
                &nbsp;&nbsp;

                <label>節點維度 (Dimension): </label>
                <select id="dimSelectC" onchange="updateChart()"></select>

                <br><br>
                <label><input type="checkbox" id="toggleAnim" onchange="toggleAnimation()"> 啟用流量粒子動畫 (Enable Traffic Animation)</label>
            </fieldset>
            <br><br>
            <span style="color: #666; font-size: 0.9em;">提示：Mode C 會顯示該拓撲下所有通道的熱點分佈圖 (Heatmap)。紅色代表高負載，藍色代表低負載。啟用動畫可以直觀感受網路擁塞狀態。</span>
        </div>

        <div id="modeDControls" class="controls" style="display: none;">
            <fieldset style="border: 1px solid #911eb4; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>成本權重設定 (Cost Weights)</strong></legend>

                <label>路由器權重 (Router Weight): </label>
                <input type="number" id="weightRouter" value="1.0" step="0.1" style="width: 60px;" onchange="updateChart()">
                &nbsp;&nbsp;

                <label>通道權重 (Channel Weight): </label>
                <input type="number" id="weightChannel" value="0.5" step="0.1" style="width: 60px;" onchange="updateChart()">
                &nbsp;&nbsp;

                <label>緩衝區權重 (Buffer Weight): </label>
                <input type="number" id="weightBuffer" value="0.2" step="0.1" style="width: 60px;" onchange="updateChart()">
                &nbsp;&nbsp;

                <label>Y 軸效能指標 (Y-Axis Performance): </label>
                <select id="paretoY" onchange="updateChart()">
                    <option value="booksim_total_throughput" selected>總吞吐量 (Total Throughput, 越高越好)</option>
                    <option value="booksim_actual_sat_rate">實際飽和點 (Saturation Rate, 越高越好)</option>
                </select>
            </fieldset>
            <br><br>
            <span style="color: #666; font-size: 0.9em;">提示：總成本 = (Nodes * Router_W) + (Channels * Channel_W) + (Nodes * Ports * Buffers * Buffer_W)。X 軸會將成本對最小值進行正規化 (1.0 = 最低成本)。</span>
        </div>

        <div id="modeEControls" class="controls" style="display: none;">
            <fieldset style="border: 1px solid #e6194b; padding: 15px; border-radius: 5px; text-align: left; display: inline-block;">
                <legend><strong>選擇比較架構 (Select Architectures to Compare)</strong></legend>

                <div style="margin-bottom: 10px;">
                    <label style="color: rgba(255, 99, 132, 1); font-weight: bold;">架構 1 (Architecture 1): </label>
                    <select id="radarConfig1" onchange="updateChart()"><option value="none">無 (None)</option></select>
                </div>

                <div style="margin-bottom: 10px;">
                    <label style="color: rgba(54, 162, 235, 1); font-weight: bold;">架構 2 (Architecture 2): </label>
                    <select id="radarConfig2" onchange="updateChart()"><option value="none">無 (None)</option></select>
                </div>

                <div>
                    <label style="color: rgba(75, 192, 192, 1); font-weight: bold;">架構 3 (Architecture 3): </label>
                    <select id="radarConfig3" onchange="updateChart()"><option value="none">無 (None)</option></select>
                </div>
            </fieldset>
            <br><br>
            <span style="color: #666; font-size: 0.9em;">提示：雷達圖顯示的五項指標皆已進行正規化（分數 0~100）。<br>
            Hops、Max Load、Zero-Load Latency 越低越好（轉換後分數越高代表表現越好）；<br>
            Saturation Rate、Throughput 越高越好。雷達圖面積越大代表綜合表現越佳。</span>
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
            document.getElementById('modeDControls').style.display = 'none';
            document.getElementById('modeEControls').style.display = 'none';
            document.getElementById('btnModeA').style.backgroundColor = '#ccc';
            document.getElementById('btnModeB').style.backgroundColor = '#ccc';
            document.getElementById('btnModeC').style.backgroundColor = '#ccc';
            document.getElementById('btnModeD').style.backgroundColor = '#ccc';
            document.getElementById('btnModeE').style.backgroundColor = '#ccc';

            if (mode === 'A') {{
                document.getElementById('modeAControls').style.display = 'block';
                document.getElementById('btnModeA').style.backgroundColor = '#3cb44b';
            }} else if (mode === 'B') {{
                document.getElementById('modeBControls').style.display = 'block';
                document.getElementById('btnModeB').style.backgroundColor = '#4363d8';
            }} else if (mode === 'C') {{
                document.getElementById('modeCControls').style.display = 'block';
                document.getElementById('btnModeC').style.backgroundColor = '#f58231';
            }} else if (mode === 'D') {{
                document.getElementById('modeDControls').style.display = 'block';
                document.getElementById('btnModeD').style.backgroundColor = '#911eb4';
            }} else if (mode === 'E') {{
                document.getElementById('modeEControls').style.display = 'block';
                document.getElementById('btnModeE').style.backgroundColor = '#e6194b';
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

        function populateRadarConfigs() {{
            let configSet = new Set();
            allData.forEach(d => {{
                if(d.theory_avg_hops !== undefined) {{
                    configSet.add(`${{d.topology}}-${{d.dim}}`);
                }}
            }});
            let configs = Array.from(configSet).sort();

            ['radarConfig1', 'radarConfig2', 'radarConfig3'].forEach(id => {{
                const select = document.getElementById(id);
                configs.forEach(c => {{
                    let opt = document.createElement('option');
                    opt.value = c;
                    let parts = c.split('-');
                    opt.text = `${{parts[0].toUpperCase()}} (Dim: ${{parts[1]}})`;
                    select.add(opt);
                }});
            }});

            // set defaults
            if (configs.length > 0) document.getElementById('radarConfig1').value = configs[0];
            if (configs.length > 1) document.getElementById('radarConfig2').value = configs[1];
        }}

        // 預設顏色庫
        const colors = [
            '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
            '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'
        ];

        let myChart = null;
        let modeA_historyDatasets = []; // Store history curves for Mode A

        function clearHistory() {{
            modeA_historyDatasets = [];
            updateChart();
        }}

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

                // Add historical datasets if keep curves is checked
                const keepCurves = document.getElementById('keepCurves').checked;
                if (keepCurves) {{
                    datasets = [...modeA_historyDatasets];
                }} else {{
                    modeA_historyDatasets = []; // reset if unchecked
                }}

                // calculate color offset based on existing datasets
                const colorOffset = datasets.length;

                filteredData.forEach((d, index) => {{
                    let label = `${{topo.toUpperCase()}} - `;
                    if (compareBy === 'routing') label += `Routing: ${{d.routing}} (Nodes: ${{d.nodes}})`;
                    else if (compareBy === 'traffic') label += `Traffic: ${{d.traffic}} (Nodes: ${{d.nodes}})`;
                    else if (compareBy === 'packet_size') label += `Packet: ${{d.packet_size}} flits (Nodes: ${{d.nodes}})`;
                    else if (compareBy === 'buffer_size') label += `Buffer: ${{d.buffer_size}} flits (Nodes: ${{d.nodes}})`;
                    else if (compareBy === 'vcs') label += `VCs: ${{d.vcs}} (Nodes: ${{d.nodes}})`;
                    else if (compareBy === 'dim') label += `Nodes: ${{d.nodes}} (R:${{d.routing}}, P:${{d.packet_size}}, B:${{d.buffer_size}}, V:${{d.vcs}})`;
                    else label += `Nodes: ${{d.nodes}}`;

                    const newDs = {{
                        label: label,
                        data: d.curve,
                        borderColor: colors[(index + colorOffset) % colors.length],
                        backgroundColor: colors[(index + colorOffset) % colors.length],
                        fill: false,
                        tension: 0.1,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }};
                    datasets.push(newDs);

                    if (keepCurves) {{
                        modeA_historyDatasets.push(newDs);
                    }}
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
                const pSizeB = document.getElementById('pSelectB').value;
                const bSizeB = document.getElementById('bSelectB').value;
                const vcsB = document.getElementById('vSelectB').value;

                let baseData = allData;
                if (pSizeB !== 'all') baseData = baseData.filter(d => d.packet_size == parseInt(pSizeB));
                if (bSizeB !== 'all') baseData = baseData.filter(d => d.buffer_size == parseInt(bSizeB));
                if (vcsB !== 'all') baseData = baseData.filter(d => d.vcs == parseInt(vcsB));

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
                            points.push({{
                                x: xVal,
                                y: yVal,
                                _meta: `Nodes: ${{d.nodes}} (Dim:${{d.dim}}, P:${{d.packet_size}}, B:${{d.buffer_size}}, VC:${{d.vcs}})`
                            }});
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
                            tooltip: {{ callbacks: {{ label: function(context) {{ return context.dataset.label + ' ' + context.raw._meta + ' | X: ' + context.parsed.x.toFixed(2) + ', Y: ' + context.parsed.y.toFixed(2); }} }} }},
                            legend: {{ position: 'right' }}
                        }}
                    }}
                }});
            }} else if (currentMode === 'D') {{
                // ===== MODE D: Pareto Plot =====
                const wRouter = parseFloat(document.getElementById('weightRouter').value);
                const wChannel = parseFloat(document.getElementById('weightChannel').value);
                const wBuffer = parseFloat(document.getElementById('weightBuffer').value);
                const yMetric = document.getElementById('paretoY').value;
                const yLabel = document.getElementById('paretoY').options[document.getElementById('paretoY').selectedIndex].text;

                // Calculate costs and find min
                let paretoData = [];
                let minCost = Infinity;

                for (let i = 0; i < allData.length; i++) {{
                    const d = allData[i];
                    if (d[yMetric] !== undefined && d[yMetric] !== null && d.theory_channel_count !== undefined) {{
                        // Assuming 5 ports per router as a baseline heuristic
                        const ports = 5;
                        const cost = (d.nodes * wRouter) + (d.theory_channel_count * wChannel) + (d.nodes * ports * d.buffer_size * wBuffer);
                        if (cost < minCost) minCost = cost;

                        paretoData.push({{
                            config: `${{d.topology}} dim:${{d.dim}} nodes:${{d.nodes}} P:${{d.packet_size}} B:${{d.buffer_size}} VC:${{d.vcs}}`,
                            cost: cost,
                            yValue: d[yMetric],
                            topo: d.topology
                        }});
                    }}
                }}

                // Normalize cost
                paretoData.forEach(p => {{
                    p.normCost = p.cost / minCost;
                }});

                // Group by topology for coloring
                const colors = {{
                    'mesh': 'rgba(255, 99, 132, 0.7)',
                    'torus': 'rgba(54, 162, 235, 0.7)',
                    'ring': 'rgba(75, 192, 192, 0.7)'
                }};

                const datasets = [];
                ['mesh', 'torus', 'ring'].forEach(t => {{
                    const filtered = paretoData.filter(d => d.topo === t);
                    if(filtered.length > 0) {{
                        datasets.push({{
                            label: t.toUpperCase(),
                            data: filtered.map(d => ({{x: d.normCost, y: d.yValue, _meta: d.config}})),
                            backgroundColor: colors[t],
                            pointRadius: 6,
                            pointHoverRadius: 8
                        }});
                    }}
                }});

                myChart = new Chart(ctx, {{
                    type: 'scatter',
                    data: {{ datasets: datasets }},
                    options: {{
                        responsive: true, maintainAspectRatio: false,
                        scales: {{
                            x: {{
                                type: 'linear',
                                title: {{ display: true, text: '正規化硬體成本 (Normalized Cost) [越低越好]', font: {{ size: 14, weight: 'bold' }} }}
                            }},
                            y: {{
                                title: {{ display: true, text: yLabel, font: {{ size: 14, weight: 'bold' }} }}
                            }}
                        }},
                        plugins: {{
                            tooltip: {{ callbacks: {{ label: function(context) {{ return context.raw._meta + ' | 成本: ' + context.parsed.x.toFixed(2) + 'x, 效能: ' + context.parsed.y.toFixed(2); }} }} }},
                            legend: {{ position: 'right' }},
                            title: {{ display: true, text: 'Design Space Pareto Plot (Cost vs Performance)', font: {{size: 16}} }}
                        }}
                    }}
                }});

            }} else if (currentMode === 'E') {{
                // ===== MODE E: Radar Chart =====
                const conf1 = document.getElementById('radarConfig1').value;
                const conf2 = document.getElementById('radarConfig2').value;
                const conf3 = document.getElementById('radarConfig3').value;

                let selectedConfigs = [conf1, conf2, conf3].filter(c => c !== 'none');

                if (selectedConfigs.length === 0) {{
                    ctx.font = '20px Arial';
                    ctx.fillText("請選擇至少一個架構進行比較", 50, 50);
                    return;
                }}

                // Gather min/max for normalization
                let metrics = ['theory_avg_hops', 'theory_max_load', 'booksim_zero_load_lat', 'booksim_actual_sat_rate', 'booksim_total_throughput'];
                let ranges = {{}};
                metrics.forEach(m => {{ ranges[m] = {{min: Infinity, max: -Infinity}}; }});

                allData.forEach(d => {{
                    metrics.forEach(m => {{
                        if (d[m] !== undefined && d[m] !== null) {{
                            if (d[m] < ranges[m].min) ranges[m].min = d[m];
                            if (d[m] > ranges[m].max) ranges[m].max = d[m];
                        }}
                    }});
                }});

                const radarColors = ['rgba(255, 99, 132, 0.5)', 'rgba(54, 162, 235, 0.5)', 'rgba(75, 192, 192, 0.5)'];
                const borderColors = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(75, 192, 192, 1)'];
                let datasets = [];

                selectedConfigs.forEach((confStr, idx) => {{
                    let parts = confStr.split('-'); // e.g. "mesh-4"
                    let t = parts[0];
                    let dim = parseInt(parts[1]);

                    // find the first corresponding data point
                    let d = allData.find(x => x.topology === t && x.dim === dim && x.theory_avg_hops !== undefined);

                    if (d) {{
                        // Normalize to 0-100 score.
                        // Lower is better for Hops, Load, Latency.
                        let scoreHops = ranges.theory_avg_hops.max !== ranges.theory_avg_hops.min ? 100 * (ranges.theory_avg_hops.max - d.theory_avg_hops) / (ranges.theory_avg_hops.max - ranges.theory_avg_hops.min) : 50;
                        let scoreLoad = ranges.theory_max_load.max !== ranges.theory_max_load.min ? 100 * (ranges.theory_max_load.max - d.theory_max_load) / (ranges.theory_max_load.max - ranges.theory_max_load.min) : 50;
                        let scoreLat = ranges.booksim_zero_load_lat.max !== ranges.booksim_zero_load_lat.min ? 100 * (ranges.booksim_zero_load_lat.max - d.booksim_zero_load_lat) / (ranges.booksim_zero_load_lat.max - ranges.booksim_zero_load_lat.min) : 50;

                        // Higher is better for Sat Rate, Throughput
                        let scoreSat = ranges.booksim_actual_sat_rate.max !== ranges.booksim_actual_sat_rate.min ? 100 * (d.booksim_actual_sat_rate - ranges.booksim_actual_sat_rate.min) / (ranges.booksim_actual_sat_rate.max - ranges.booksim_actual_sat_rate.min) : 50;
                        let scoreThru = ranges.booksim_total_throughput.max !== ranges.booksim_total_throughput.min ? 100 * (d.booksim_total_throughput - ranges.booksim_total_throughput.min) / (ranges.booksim_total_throughput.max - ranges.booksim_total_throughput.min) : 50;

                        datasets.push({{
                            label: `${{d.topology.toUpperCase()}} dim:${{d.dim}}`,
                            data: [scoreHops, scoreLoad, scoreLat, scoreSat, scoreThru],
                            fill: true,
                            backgroundColor: radarColors[idx % 3],
                            borderColor: borderColors[idx % 3],
                            pointBackgroundColor: borderColors[idx % 3],
                            pointBorderColor: '#fff',
                            pointHoverBackgroundColor: '#fff',
                            pointHoverBorderColor: borderColors[idx % 3],
                            rawValues: [d.theory_avg_hops, d.theory_max_load, d.booksim_zero_load_lat, d.booksim_actual_sat_rate, d.booksim_total_throughput]
                        }});
                    }}
                }});

                myChart = new Chart(ctx, {{
                    type: 'radar',
                    data: {{
                        labels: [
                            '理論跳數 (Avg Hops) [越低越好]',
                            '最大通道負載 (Max Load) [越低越好]',
                            '零負載延遲 (Zero-load Latency) [越低越好]',
                            '實際飽和點 (Saturation Rate) [越高越好]',
                            '總吞吐量 (Throughput) [越高越好]'
                        ],
                        datasets: datasets
                    }},
                    options: {{
                        responsive: true, maintainAspectRatio: false,
                        elements: {{ line: {{ borderWidth: 3 }} }},
                        scales: {{
                            r: {{
                                angleLines: {{ display: true }},
                                suggestedMin: 0,
                                suggestedMax: 100,
                                ticks: {{ display: false }} // hide the 0-100 internal ticks to focus on shape
                            }}
                        }},
                        plugins: {{
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        let rawLabel = context.dataset.label;
                                        let rawVal = context.dataset.rawValues[context.dataIndex];
                                        if (rawVal !== undefined && rawVal !== null) {{
                                            return `${{rawLabel}}: ${{rawVal.toFixed(2)}} (Score: ${{context.formattedValue}})`;
                                        }}
                                        return `${{rawLabel}}: ${{context.formattedValue}}`;
                                    }}
                                }}
                            }},
                            title: {{ display: true, text: 'NoC 極限壓力測試雷達圖 (Radar Chart)', font: {{size: 16}} }}
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

        let animId = null;
        let particles = [];
        let globalMaxLoad = 0;

        function toggleAnimation() {{
            if (!document.getElementById('toggleAnim').checked) {{
                if (animId) cancelAnimationFrame(animId);
                animId = null;
                particles = [];
                // Redraw static
                if(currentMode === 'C') updateChart();
            }} else {{
                if(currentMode === 'C' && heatmapEdges.length > 0) {{
                    animateHeatmap();
                }}
            }}
        }}

        function animateHeatmap() {{
            const canvas = document.getElementById('heatmapCanvas');
            const ctx = canvas.getContext('2d');

            // Randomly spawn particles based on edge load
            heatmapEdges.forEach(edge => {{
                // Probability of spawning proportional to its load relative to max
                const spawnProb = (edge.load / globalMaxLoad) * 0.1; // adjust scalar as needed
                if (Math.random() < spawnProb) {{
                    particles.push({{
                        edge: edge,
                        progress: 0,
                        speed: 0.01 + (Math.random() * 0.02)
                    }});
                }}
            }});

            // Update particles
            for (let i = particles.length - 1; i >= 0; i--) {{
                particles[i].progress += particles[i].speed;
                if (particles[i].progress >= 1) {{
                    particles.splice(i, 1);
                }}
            }}

            // Redraw base heatmap
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            renderHeatmapBase(ctx);

            // Draw particles
            ctx.fillStyle = 'yellow';
            particles.forEach(p => {{
                let x, y;
                if (p.edge.isWrapAround) {{
                    // Wrap-around paths are split into two segments: start->mid1 and mid2->end
                    if (p.progress < 0.5) {{
                        let subProgress = p.progress * 2;
                        x = p.edge.x1 + (p.edge.mid1.x - p.edge.x1) * subProgress;
                        y = p.edge.y1 + (p.edge.mid1.y - p.edge.y1) * subProgress;
                    }} else {{
                        let subProgress = (p.progress - 0.5) * 2;
                        x = p.edge.mid2.x + (p.edge.x2 - p.edge.mid2.x) * subProgress;
                        y = p.edge.mid2.y + (p.edge.y2 - p.edge.mid2.y) * subProgress;
                    }}
                }} else {{
                    x = p.edge.x1 + (p.edge.x2 - p.edge.x1) * p.progress;
                    y = p.edge.y1 + (p.edge.y2 - p.edge.y1) * p.progress;
                }}

                ctx.beginPath();
                ctx.arc(x, y, 4, 0, 2 * Math.PI);
                ctx.fill();
            }});

            if (document.getElementById('toggleAnim').checked) {{
                animId = requestAnimationFrame(animateHeatmap);
            }}
        }}

        function renderHeatmapBase(ctx) {{
            // Draw edges
            ctx.lineWidth = 4;
            for (let edge of heatmapEdges) {{
                ctx.beginPath();

                // For Torus wrap-around, draw curved or broken lines if distance is too large
                if (edge.isWrapAround) {{
                    ctx.strokeStyle = edge.color;
                    ctx.setLineDash([5, 5]); // dashed line for wrap-around

                    ctx.moveTo(edge.x1, edge.y1);
                    ctx.lineTo(edge.mid1.x, edge.mid1.y);

                    // Draw arrowhead for outgoing line
                    let dxOut = edge.mid1.x - edge.x1;
                    let dyOut = edge.mid1.y - edge.y1;
                    let angleOut = Math.atan2(dyOut, dxOut);
                    const headlen = 10;
                    ctx.moveTo(edge.mid1.x, edge.mid1.y);
                    ctx.lineTo(edge.mid1.x - headlen * Math.cos(angleOut - Math.PI / 6), edge.mid1.y - headlen * Math.sin(angleOut - Math.PI / 6));
                    ctx.moveTo(edge.mid1.x, edge.mid1.y);
                    ctx.lineTo(edge.mid1.x - headlen * Math.cos(angleOut + Math.PI / 6), edge.mid1.y - headlen * Math.sin(angleOut + Math.PI / 6));

                    ctx.moveTo(edge.mid2.x, edge.mid2.y);
                    ctx.lineTo(edge.x2, edge.y2);

                    // Draw arrowhead for incoming line (pointing towards node V)
                    let dxIn = edge.x2 - edge.mid2.x;
                    let dyIn = edge.y2 - edge.mid2.y;
                    let angleIn = Math.atan2(dyIn, dxIn);

                    const offsetTargetX = edge.x2 - 12 * Math.cos(angleIn);
                    const offsetTargetY = edge.y2 - 12 * Math.sin(angleIn);

                    ctx.moveTo(offsetTargetX, offsetTargetY);
                    ctx.lineTo(offsetTargetX - headlen * Math.cos(angleIn - Math.PI / 6), offsetTargetY - headlen * Math.sin(angleIn - Math.PI / 6));
                    ctx.moveTo(offsetTargetX, offsetTargetY);
                    ctx.lineTo(offsetTargetX - headlen * Math.cos(angleIn + Math.PI / 6), offsetTargetY - headlen * Math.sin(angleIn + Math.PI / 6));

                }} else {{
                    ctx.moveTo(edge.x1, edge.y1);
                    ctx.strokeStyle = edge.color;
                    ctx.setLineDash([]);
                    ctx.lineTo(edge.x2, edge.y2);

                    // Draw arrow head at the end
                    const dx = edge.x2 - edge.x1;
                    const dy = edge.y2 - edge.y1;
                    const angle = Math.atan2(dy, dx);
                    const headlen = 10;

                    const offsetTargetX = edge.x2 - 12 * Math.cos(angle);
                    const offsetTargetY = edge.y2 - 12 * Math.sin(angle);

                    ctx.moveTo(offsetTargetX, offsetTargetY);
                    ctx.lineTo(offsetTargetX - headlen * Math.cos(angle - Math.PI / 6), offsetTargetY - headlen * Math.sin(angle - Math.PI / 6));
                    ctx.moveTo(offsetTargetX, offsetTargetY);
                    ctx.lineTo(offsetTargetX - headlen * Math.cos(angle + Math.PI / 6), offsetTargetY - headlen * Math.sin(angle + Math.PI / 6));
                }}
                ctx.stroke();
            }}
            ctx.setLineDash([]); // reset

            // Draw nodes
            for (let node of heatmapNodes) {{
                ctx.beginPath();
                ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
                ctx.fillStyle = '#333';
                ctx.fill();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.stroke();
            }}
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
            particles = [];
            if (animId) {{
                cancelAnimationFrame(animId);
                animId = null;
            }}

            if (!edgeLoads || Object.keys(edgeLoads).length === 0) {{
                ctx.fillStyle = 'black';
                ctx.font = '20px Arial';
                ctx.fillText("尚無該拓撲的通道負載資料 (No edge load data available)", 50, 50);
                return;
            }}

            let maxLoad = 0;
            for (let key in edgeLoads) {{
                if (edgeLoads[key] > maxLoad) maxLoad = edgeLoads[key];
            }}
            globalMaxLoad = maxLoad;

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

            // Prepare edges based on edgeLoads keys (e.g., "0->1")
            for (let key in edgeLoads) {{
                const parts = key.split('->');
                if (parts.length === 2) {{
                    const u = parseInt(parts[0]);
                    const v = parseInt(parts[1]);
                    const load = edgeLoads[key];
                    const nodeU = nodes.find(n => n.id === u);
                    const nodeV = nodes.find(n => n.id === v);

                    if (nodeU && nodeV) {{
                        let isWrapAround = false;
                        if (topo === 'torus' && (Math.abs(nodeU.x - nodeV.x) > drawWidth * 0.8 || Math.abs(nodeU.y - nodeV.y) > drawHeight * 0.8)) {{
                            isWrapAround = true;
                        }}

                        // Calculate orthogonal offset vector to draw parallel lines
                        const dx = nodeV.x - nodeU.x;
                        const dy = nodeV.y - nodeU.y;
                        const length = Math.sqrt(dx * dx + dy * dy);

                        let nx = 0, ny = 0;
                        if (length > 0) {{
                            nx = -dy / length;
                            ny = dx / length;
                        }}

                        const offset = 12; // offset by 12 pixels to clearly separate bidirectional lines
                        const shiftX = nx * offset;
                        const shiftY = ny * offset;

                        heatmapEdges.push({{
                            u: u, v: v,
                            x1: nodeU.x + shiftX, y1: nodeU.y + shiftY,
                            x2: nodeV.x + shiftX, y2: nodeV.y + shiftY,
                            load: load,
                            color: getColorForLoad(load, maxLoad),
                            isWrapAround: isWrapAround
                        }});
                    }}
                }}
            }}

            // Pre-calculate wrap-around midpoints for the animation
            for (let edge of heatmapEdges) {{
                if (edge.isWrapAround) {{
                    let midX1 = edge.x1;
                    let midY1 = edge.y1;
                    let midX2 = edge.x2;
                    let midY2 = edge.y2;
                    const extend = 80;

                    if (Math.abs(edge.x1 - edge.x2) > drawWidth * 0.8) {{
                        midX1 = edge.x1 > edge.x2 ? edge.x1 + extend : edge.x1 - extend;
                        midX2 = edge.x2 > edge.x1 ? edge.x2 + extend : edge.x2 - extend;
                    }}
                    if (Math.abs(edge.y1 - edge.y2) > drawHeight * 0.8) {{
                        midY1 = edge.y1 > edge.y2 ? edge.y1 + extend : edge.y1 - extend;
                        midY2 = edge.y2 > edge.y1 ? edge.y2 + extend : edge.y2 - extend;
                    }}
                    edge.mid1 = {{x: midX1, y: midY1}};
                    edge.mid2 = {{x: midX2, y: midY2}};
                }}
            }}

            // Start animation or just draw base
            if (document.getElementById('toggleAnim').checked) {{
                if (!animId) animateHeatmap();
            }} else {{
                renderHeatmapBase(ctx);
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

            populateSelect('pSelectB', allOptions.packet_size, true);
            populateSelect('bSelectB', allOptions.buffer_size, true);
            populateSelect('vSelectB', allOptions.vcs, true);

            populateSelect('topoSelectC', allOptions.topology, false);
            populateSelect('dimSelectC', dims, false);

            populateRadarConfigs();

            // 設定預設選項並更新
            if(allOptions.topology.includes('ring')) {{
                document.getElementById('topoSelect').value = 'ring';
                document.getElementById('topoSelectC').value = 'ring';
            }}
            document.getElementById('pSelectB').value = '1';
            document.getElementById('bSelectB').value = '8';
            updateChart();
        }};
    </script>
    </body>
    </html>
    """

    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "interactive_dse_trends.html")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"互動式 HTML 報告已產生：{output_path}")

if __name__ == "__main__":
    generate_interactive_html()
