import os
import sys
import json
import numpy as np
from scipy.optimize import curve_fit

# Add root directory to sys.path to access scripts/html_gen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.data_utils import load_json
from scripts.html_gen.lib.html_utils import create_html_scaffold, save_html

def queue_delay_func(rate, base, max_rate, scaling):
    y = np.full_like(rate, np.inf, dtype=float)
    valid = rate < max_rate
    y[valid] = base + scaling * (rate[valid] / (max_rate - rate[valid]))
    return y

def generate_dashboard():
    # --- 1. Load Data ---
    print("Loading data...")
    v_results = load_json(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports", "cross_verification", "data", "verification_results.json"), [])
    r_results = load_json(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports", "uniform_dse", "data", "report_full_booksim_ring.json"), {})
    micro_data = load_json(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports", "uniform_dse", "data", "micro_metrics_results.json"), [])
    c_model_data = load_json(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports", "c_model_eval", "data", "c_model_sweep_results.json"), [])

    # --- 2. Process Macro DSE Data (Tab 1) ---
    unified_data = []
    for r in v_results:
        vcs = r.get('vcs') if 'vcs' in r else (1 if r['topology'] == 'mesh' else 2)
        routing = r.get('routing', 'xy' if r['topology'] == 'mesh' else 'dim_order')
        traffic = r.get('traffic', 'uniform')
        record = {
            "topology": r['topology'],
            "dim": r['dim'],
            "nodes": r.get('nodes', r['dim']*r['dim'] if r['topology']!='ring' else r['dim']),
            "routing": routing,
            "traffic": traffic,
            "packet_size": r.get('packet_size', 1),
            "buffer_size": r.get('buffer_size', 8),
            "vcs": vcs,
            "curve": [ {"x": pt['rate'], "y": pt['latency']} for pt in r.get('latency_curve', []) if pt['latency'] != float('inf') ]
        }
        if record["curve"]:
            unified_data.append(record)

    for key, runs in r_results.items():
        dim = int(key.split('_')[1])
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
            points.sort(key=lambda pt: pt['x'])
            record = {
                "topology": "ring",
                "dim": dim,
                "nodes": dim,
                "routing": rt,
                "traffic": tr,
                "packet_size": p,
                "buffer_size": b,
                "vcs": v,
                "curve": points
            }
            unified_data.append(record)

    # --- 3. Process Micro Data & Curve Fitting (Tab 2) ---
    rates_micro = []
    lats_micro = []
    for pt in micro_data:
        if pt['latency'] != float('inf'):
            rates_micro.append(pt['rate'])
            lats_micro.append(pt['latency'])

    rates_arr = np.array(rates_micro)
    lats_arr = np.array(lats_micro)

    base_fit, max_rate_fit, scaling_fit = 0, 0, 0
    if len(rates_arr) >= 3:
        p0 = [min(lats_arr), max(rates_arr) + 0.05, 1.0]
        bounds = ([0, max(rates_arr), 0], [np.inf, 1.0, np.inf])
        try:
            popt, _ = curve_fit(queue_delay_func, rates_arr, lats_arr, p0=p0, bounds=bounds)
            base_fit, max_rate_fit, scaling_fit = popt
        except:
            pass

    fitRates = []
    fitLats = []
    if max_rate_fit > 0:
        r_step = 0.01
        r = 0.01
        while r <= max_rate_fit - 0.01:
            fitRates.append(r)
            l = base_fit + scaling_fit * (r / (max_rate_fit - r))
            fitLats.append(l)
            r += r_step

    # --- 4. Process Cross Verification Data (Tab 3) ---
    v_results_sorted = sorted(v_results, key=lambda x: (x.get('topology',''), x.get('dim',0)))

    # --- 5. Process C-Model Data (Tab 4) ---
    # Need to match C-model data with corresponding Booksim curve
    # Currently C-model is mesh 4x4 uniform. We find the matching curve in unified_data.
    c_booksim_curve = []
    for r in unified_data:
        if r['topology'] == 'mesh' and r['dim'] == 4 and r['traffic'] == 'uniform':
            c_booksim_curve = r['curve']
            break

    c_model_points = [{"x": pt['rate'], "y": pt['latency']} for pt in c_model_data if pt['latency'] != float('inf')]
    c_model_thr = [{"x": pt['rate'], "y": pt['throughput']} for pt in c_model_data]

    # --- HTML Generation ---
    print("Generating HTML structure...")

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8">
    <title>Unified NoC Design Space Exploration Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.css">
    <script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background-color: #f4f7f6; color: #333; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
        .nav-tabs {{ display: flex; background-color: #34495e; padding: 0 20px; }}
        .nav-tabs button {{ background-color: inherit; color: #ecf0f1; border: none; padding: 14px 20px; cursor: pointer; font-size: 16px; font-weight: bold; transition: 0.3s; }}
        .nav-tabs button:hover {{ background-color: #1abc9c; }}
        .nav-tabs button.active {{ background-color: #1abc9c; border-bottom: 3px solid #ecf0f1; }}

        .tab-content {{ display: none; padding: 20px; max-width: 1200px; margin: auto; background: white; box-shadow: 0px 0px 10px rgba(0,0,0,0.1); min-height: 80vh; }}
        .tab-content.active {{ display: block; }}

        .card {{ border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 20px; background-color: #fafafa; }}
        .controls select, .controls button {{ padding: 8px; margin: 5px; border-radius: 4px; border: 1px solid #ccc; }}

        /* Table Styles */
        table.custom-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        table.custom-table th, table.custom-table td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
        table.custom-table th {{ background-color: #34495e; color: white; }}

        /* Canvas container */
        .chart-container {{ position: relative; height: 500px; width: 100%; }}
    </style>
</head>
<body>

    <div class="header">
        <h1>Unified NoC DSE Dashboard</h1>
        <p>Comprehensive Performance, Theory, and Verification Analysis</p>
    </div>

    <div class="nav-tabs">
        <button class="tab-links active" onclick="openTab(event, 'TabMacro')">1. Macro DSE</button>
        <button class="tab-links" onclick="openTab(event, 'TabMicro')">2. Micro & Queueing Theory</button>
        <button class="tab-links" onclick="openTab(event, 'TabVerify')">3. Cross-Engine Verification</button>
        <button class="tab-links" onclick="openTab(event, 'TabCModel')">4. C-Model Evaluation</button>
    </div>

    <!-- TAB 1: Macro DSE -->
    <div id="TabMacro" class="tab-content active">
        <h2>巨觀設計空間探索 (Macro DSE)</h2>
        <div class="card controls">
            <label>拓撲 (Topology): </label><select id="topoSelect" onchange="updateMacroChart()"></select>
            <label>流量 (Traffic): </label><select id="trafficSelect" onchange="updateMacroChart()"></select>
            <label>VC數: </label><select id="vcSelect" onchange="updateMacroChart()"></select>
        </div>
        <div class="card chart-container">
            <canvas id="macroChart"></canvas>
        </div>
    </div>

    <!-- TAB 2: Micro & Queueing Theory -->
    <div id="TabMicro" class="tab-content">
        <h2>微觀排隊與緩衝區理論 (Micro & Queueing Theory)</h2>
        <div class="card">
            <h3>非線性延遲曲線擬合 (M/D/1 預估)</h3>
            <p><strong>擬合公式:</strong> L = Base + Scaling * [ Rate / (Max_Rate - Rate) ]</p>
            <ul>
                <li><strong>Base Latency:</strong> {base_fit:.4f} cycles</li>
                <li><strong>Max Rate (Saturation):</strong> {max_rate_fit:.4f} flits/cycle</li>
                <li><strong>Scaling Factor:</strong> {scaling_fit:.4f}</li>
            </ul>
            <div class="chart-container" style="height: 400px;">
                <canvas id="microChart"></canvas>
            </div>
        </div>
        <div class="card">
            <h3>緩衝區佔用與延遲變異數</h3>
            <table class="custom-table">
                <tr><th>Injection Rate</th><th>Avg Latency</th><th>Max Latency</th><th>Variance</th><th>Avg Buffer Writes/Port</th></tr>
"""
    for pt in micro_data:
        lat_str = f"{pt['latency']:.2f}" if pt['latency'] != float('inf') else "Saturation"
        html += f"<tr><td>{pt['rate']}</td><td>{lat_str}</td><td>{pt['max_latency']}</td><td>{pt['variance']:.2f}</td><td>{pt.get('avg_buffer_writes', 0.0):.2f}</td></tr>"

    html += """
            </table>
        </div>
    </div>

    <!-- TAB 3: Cross-Engine Verification -->
    <div id="TabVerify" class="tab-content">
        <h2>跨引擎交叉驗證 (Cross-Engine Verification)</h2>
        <div class="card">
            <table id="verifyTable" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Topology</th>
                        <th>Dim</th>
                        <th>Theory Channels</th>
                        <th>Actual Channels</th>
                        <th>Theory Bisec BW</th>
                        <th>Theory Max Load</th>
                        <th>1 / Sat Rate</th>
                        <th>Theory Max Rate</th>
                        <th>Actual Sat Rate</th>
                    </tr>
                </thead>
                <tbody>
"""
    for r in v_results_sorted:
        t_chan = r.get('theory_channel_count', 'N/A')
        a_chan = "N/A"
        t_bw = r.get('theory_bisection_bw', 'N/A')
        t_load = f"{r['theory_max_load']:.4f}" if r.get('theory_max_load') else "N/A"

        sat_rate = r.get('booksim_actual_sat_rate')
        inv_sat = f"{(1.0 / sat_rate):.4f}" if sat_rate and sat_rate > 0 else "N/A"

        t_rate = f"{r['theory_max_rate']:.4f}" if r.get('theory_max_rate') else "N/A"
        a_rate = f"{sat_rate:.4f}" if sat_rate else "N/A"

        html += f"<tr><td>{r.get('topology','').capitalize()}</td><td>{r.get('dim','')}</td><td>{t_chan}</td><td>{a_chan}</td><td>{t_bw}</td><td>{t_load}</td><td>{inv_sat}</td><td>{t_rate}</td><td>{a_rate}</td></tr>"

    html += """
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 4: C-Model Evaluation -->
    <div id="TabCModel" class="tab-content">
        <h2>C++ 模型精準度分析 (C-Model Evaluation)</h2>
        <div class="card">
            <p>比較 Phase 2 開發的 C++ Functional Model 與 Cycle-Accurate BookSim 的差異。C Model 為了加速模擬，在 Routing 與 Arbitration 採用了簡化的理想週期模型，因此 Zero-load Latency 較低，但吞吐量縮放與飽和點應保持一致。</p>
            <div class="chart-container">
                <canvas id="cmodelChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        // --- Tab Switching Logic ---
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tablinks = document.getElementsByClassName("tab-links");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }

        // --- Data Variables ---
        const macroData = """ + json.dumps(unified_data) + """;
        const fitRates = """ + json.dumps(fitRates) + """;
        const fitLats = """ + json.dumps(fitLats) + """;
        const microRates = """ + json.dumps(rates_micro) + """;
        const microLats = """ + json.dumps(lats_micro) + """;

        const cModelPoints = """ + json.dumps(c_model_points) + """;
        const cBooksimPoints = """ + json.dumps(c_booksim_curve) + """;

        // --- Tab 1: Macro DSE Chart ---
        let macroChartObj = null;
        function initMacroControls() {
            let topos = new Set();
            let traffics = new Set();
            let vcs = new Set();
            macroData.forEach(d => {
                topos.add(d.topology);
                traffics.add(d.traffic);
                vcs.add(d.vcs);
            });

            const pSel = (id, set, def) => {
                const el = document.getElementById(id);
                Array.from(set).sort().forEach(v => {
                    let opt = document.createElement("option");
                    opt.value = v; opt.text = v;
                    if(v === def) opt.selected = true;
                    el.appendChild(opt);
                });
            };
            pSel('topoSelect', topos, 'mesh');
            pSel('trafficSelect', traffics, 'uniform');
            pSel('vcSelect', vcs, 2);
        }

        function updateMacroChart() {
            const t = document.getElementById('topoSelect').value;
            const tr = document.getElementById('trafficSelect').value;
            const v = parseInt(document.getElementById('vcSelect').value);

            const filtered = macroData.filter(d => d.topology === t && d.traffic === tr && d.vcs === v);

            const datasets = filtered.map((d, i) => {
                const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6'];
                const c = colors[i % colors.length];
                return {
                    label: `${d.topology}_${d.dim}x${d.dim} (Nodes:${d.nodes})`,
                    data: d.curve,
                    borderColor: c,
                    backgroundColor: c,
                    fill: false,
                    tension: 0.1
                };
            });

            if (macroChartObj) macroChartObj.destroy();
            macroChartObj = new Chart(document.getElementById('macroChart'), {
                type: 'line',
                data: { datasets: datasets },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: { type: 'linear', title: { display: true, text: 'Injection Rate' } },
                        y: { title: { display: true, text: 'Latency (cycles)' } }
                    }
                }
            });
        }

        // --- Tab 2: Micro Chart ---
        new Chart(document.getElementById('microChart'), {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'BookSim Empirical',
                        data: microRates.map((r, i) => ({x: r, y: microLats[i]})),
                        borderColor: '#2980b9', backgroundColor: '#2980b9', showLine: false, pointRadius: 6
                    },
                    {
                        label: 'Queueing Theory Fit',
                        data: fitRates.map((r, i) => ({x: r, y: fitLats[i]})),
                        borderColor: '#e74c3c', borderDash: [5, 5], fill: false, pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { type: 'linear', title: { display: true, text: 'Injection Rate' } },
                    y: { title: { display: true, text: 'Latency' }, max: 2000 }
                }
            }
        });

        // --- Tab 3: DataTable ---
        $(document).ready(function() {
            $('#verifyTable').DataTable({
                "pageLength": 15,
                "order": [[ 0, "asc" ], [ 1, "asc" ]]
            });
        });

        // --- Tab 4: C-Model Chart ---
        new Chart(document.getElementById('cmodelChart'), {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'C++ Model Latency',
                        data: cModelPoints,
                        borderColor: '#8e44ad', backgroundColor: '#8e44ad', fill: false, tension: 0.1
                    },
                    {
                        label: 'BookSim Baseline Latency',
                        data: cBooksimPoints,
                        borderColor: '#27ae60', borderDash: [5, 5], fill: false, tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { type: 'linear', title: { display: true, text: 'Injection Rate' } },
                    y: { title: { display: true, text: 'Latency (cycles)' } }
                }
            }
        });

        // Init Tab 1
        initMacroControls();
        updateMacroChart();

    </script>
</body>
</html>
"""

    out_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports", "unified_dashboard", "index.html")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print("Unified Dashboard successfully generated at reports/Unified_NoC_Dashboard.html")

if __name__ == "__main__":
    generate_dashboard()
