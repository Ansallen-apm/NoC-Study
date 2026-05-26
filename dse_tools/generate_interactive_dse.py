import json
import os

def generate_interactive_html():
    unified_data = []

    # 1. 讀取 verification_results.json (主要是 Mesh/Torus/Ring 固定參數的掃描)
    if os.path.exists('report/verification_results.json'):
        with open('report/verification_results.json', 'r', encoding='utf-8') as f:
            v_results = json.load(f)
            for r in v_results:
                # 這裡的預設參數對應 verify_cross_correlation.py 的設定
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
                    "curve": [ {"x": pt['rate'], "y": pt['latency']} for pt in r.get('latency_curve', []) if pt['latency'] != float('inf') ]
                }
                if record["curve"]:
                    unified_data.append(record)

    # 2. 讀取 report_full_booksim_ring.json (Ring 拓撲的龐大參數矩陣掃描)
    if os.path.exists('report/report_full_booksim_ring.json'):
        with open('report/report_full_booksim_ring.json', 'r', encoding='utf-8') as f:
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

        <div class="controls">
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

        <div class="chart-container">
            <canvas id="dseChart"></canvas>
        </div>
    </div>

    <script>
        // 來自 Python 的完整 DSE 曲線資料與選項
        const allData = {chart_data_json};
        const allOptions = {options_json};

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
            const topo = document.getElementById('topoSelect').value;
            const routing = document.getElementById('rSelect').value;
            const traffic = document.getElementById('tSelect').value;
            const pSize = document.getElementById('pSelect').value;
            const bSize = document.getElementById('bSelect').value;
            const vcs = document.getElementById('vSelect').value;
            const compareBy = document.getElementById('compareSelect').value;

            // 1. 過濾資料
            let filteredData = allData.filter(d => d.topology === topo);

            if (compareBy !== 'routing' && routing !== 'all') {{
                filteredData = filteredData.filter(d => d.routing === routing);
            }}
            if (compareBy !== 'traffic' && traffic !== 'all') {{
                filteredData = filteredData.filter(d => d.traffic === traffic);
            }}
            if (compareBy !== 'packet_size' && pSize !== 'all') {{
                filteredData = filteredData.filter(d => d.packet_size == parseInt(pSize));
            }}
            if (compareBy !== 'buffer_size' && bSize !== 'all') {{
                filteredData = filteredData.filter(d => d.buffer_size == parseInt(bSize));
            }}
            if (compareBy !== 'vcs' && vcs !== 'all') {{
                filteredData = filteredData.filter(d => d.vcs == parseInt(vcs));
            }}

            // 對於 dim，我們預設如果是 compareBy == dim 就全抓，
            // 若不是 compareBy == dim，我們預設只挑 nodes 最大的來看
            if (compareBy !== 'dim') {{
                if (filteredData.length > 0) {{
                    const maxNodes = Math.max(...filteredData.map(d => d.nodes));
                    filteredData = filteredData.filter(d => d.nodes === maxNodes);
                }}
            }}

            // 2. 轉換為 Chart.js 的 Dataset 格式
            let datasets = [];
            filteredData.forEach((d, index) => {{
                // 決定 Label 名稱
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

            const ctx = document.getElementById('dseChart').getContext('2d');

            if (myChart) {{
                myChart.destroy();
            }}

            if (datasets.length === 0) {{
                /* 若沒有符合條件的資料，畫一個空的以防報錯 */
                datasets = [{{ label: '無符合資料 (No Data)', data: [] }}];
            }}

            myChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{
                                display: true,
                                text: '注入率 (Injection Rate) [flits/node/cycle]',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            min: 0
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: '平均延遲 (Average Latency) [cycles]',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            min: 0,
                            suggestedMax: 100 // 可避免 Y 軸被單一飆高的點拉得太誇張
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': Rate ' + context.parsed.x + ' -> Latency ' + context.parsed.y + ' cycles';
                                }}
                            }}
                        }},
                        legend: {{
                            position: 'right'
                        }}
                    }}
                }}
            }});
        }}

        // 初始化
        window.onload = function() {{
            // 填入下拉選項 (Topology 不給 All)
            populateSelect('topoSelect', allOptions.topology, false);
            populateSelect('rSelect', allOptions.routing, true);
            populateSelect('tSelect', allOptions.traffic, true);
            populateSelect('pSelect', allOptions.packet_size, true);
            populateSelect('bSelect', allOptions.buffer_size, true);
            populateSelect('vSelect', allOptions.vcs, true);

            // 設定預設選項並更新
            if(allOptions.topology.includes('ring')) document.getElementById('topoSelect').value = 'ring';
            updateChart();
        }};
    </script>
    </body>
    </html>
    """

    output_path = 'report/interactive_dse_trends.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"互動式 HTML 報告已產生：{output_path}")

if __name__ == "__main__":
    generate_interactive_html()
