import os
import json
import numpy as np

def load_json(filepath, default_val=None):
    if default_val is None:
        default_val = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return default_val

def get_base_metrics_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports")

def generate_cmp_dashboard():
    reports_dir = get_base_metrics_path()

    # 1. Load Data
    v_results = load_json(os.path.join(reports_dir, 'verification_results.json'), [])
    c_model_data = load_json(os.path.join(reports_dir, 'c_model_sweep_results.json'), [])
    micro_data = load_json(os.path.join(reports_dir, 'micro_metrics_results.json'), [])

    # 2. Aggregation Dictionary
    # Key: (topology, dim, traffic, routing, vcs)
    # Value: dict containing datasets for 'booksim', 'c_model', 'python_md1'
    aggregated_data = {}

    # 2.1 Process BookSim (from verification_results)
    for r in v_results:
        topo = r.get('topology', 'mesh')
        dim = r.get('dim', 4)
        traffic = r.get('traffic', 'uniform')
        routing = r.get('routing', 'xy' if topo == 'mesh' else 'dim_order')
        vcs = r.get('vcs', 1 if topo == 'mesh' else 2)

        key = (topo, dim, traffic, routing, vcs)
        if key not in aggregated_data:
            aggregated_data[key] = {"booksim": [], "c_model": [], "python_md1": []}

        curve = [ {"x": pt['rate'], "y": pt['latency'], "thr": pt.get('throughput', pt['rate'] * (dim*dim if topo!='ring' else dim))} for pt in r.get('latency_curve', []) if pt['latency'] != float('inf') ]
        aggregated_data[key]["booksim"] = curve

    # 2.2 Process C-Model
    # Note: Currently c_model runner hardcodes mesh 4x4 uniform xy vcs=1 (from yaml).
    # For a generalized framework, we assume it's Mesh 4x4 for now based on current runner constraints.
    # In the future, c_model_runner can dump its actual config. We map what we have.
    c_key = ('mesh', 4, 'uniform', 'xy', 1)
    if c_model_data and c_key not in aggregated_data:
        aggregated_data[c_key] = {"booksim": [], "c_model": [], "python_md1": []}

    c_curve = [{"x": pt['rate'], "y": pt['latency'], "thr": pt['throughput']} for pt in c_model_data if pt['latency'] != float('inf')]
    if c_key in aggregated_data:
        aggregated_data[c_key]["c_model"] = c_curve

    # 2.3 Process Python M/D/1 (from micro_metrics curve fit)
    # We fit the micro_data to get Base and Scaling, then generate points
    # Micro metrics runner defaults to Mesh 4x4 uniform dim_order(xy) vcs=2
    m_key = ('mesh', 4, 'uniform', 'xy', 2)
    if micro_data and m_key not in aggregated_data:
        aggregated_data[m_key] = {"booksim": [], "c_model": [], "python_md1": []}

    rates_micro = [pt['rate'] for pt in micro_data if pt['latency'] != float('inf')]
    lats_micro = [pt['latency'] for pt in micro_data if pt['latency'] != float('inf')]

    python_md1_curve = []
    if len(rates_micro) >= 3:
        from scipy.optimize import curve_fit
        def queue_delay_func(rate, base, max_rate, scaling):
            y = np.full_like(rate, np.inf, dtype=float)
            valid = rate < max_rate
            y[valid] = base + scaling * (rate[valid] / (max_rate - rate[valid]))
            return y

        rates_arr = np.array(rates_micro)
        lats_arr = np.array(lats_micro)
        p0 = [min(lats_arr), max(rates_arr) + 0.05, 1.0]
        bounds = ([0, max(rates_arr), 0], [np.inf, 1.0, np.inf])
        try:
            popt, _ = curve_fit(queue_delay_func, rates_arr, lats_arr, p0=p0, bounds=bounds)
            base_fit, max_rate_fit, scaling_fit = popt

            r = 0.01
            while r <= max_rate_fit - 0.01:
                lat = base_fit + scaling_fit * (r / (max_rate_fit - r))
                python_md1_curve.append({"x": r, "y": lat})
                r += 0.01
        except:
            pass

    if m_key in aggregated_data:
        aggregated_data[m_key]["python_md1"] = python_md1_curve

    # Prepare JS data structure
    js_data = []
    for (t, d, tr, r, v), models in aggregated_data.items():
        if len(models["booksim"]) > 0 or len(models["c_model"]) > 0 or len(models["python_md1"]) > 0:
            js_data.append({
                "topology": t, "dim": d, "traffic": tr, "routing": r, "vcs": v,
                "models": models
            })

    # Write JSON variable to a separate file or directly embed
    return js_data




    # ... appending to the existing file

def generate_html(js_data):
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8">
    <title>Multi-Model Comparison Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f8f9fa; color: #333; }}
        .header {{ background: #34495e; color: white; padding: 20px; text-align: center; }}
        .container {{ display: flex; max-width: 1400px; margin: 20px auto; gap: 20px; }}

        .sidebar {{ width: 280px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: fit-content; }}
        .sidebar label {{ font-weight: bold; display: block; margin-top: 15px; margin-bottom: 5px; }}
        .sidebar select {{ width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #ccc; }}

        .main-content {{ flex: 1; display: flex; flex-direction: column; gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .chart-container {{ position: relative; height: 400px; width: 100%; }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
        th {{ background: #ecf0f1; }}
        .err-good {{ color: green; font-weight: bold; }}
        .err-bad {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>

    <div class="header">
        <h1>Multi-Model Comparison Dashboard</h1>
        <p>疊加對比 Python Theory vs. BookSim vs. C-Model</p>
    </div>

    <div class="container">
        <!-- Sidebar Filters -->
        <div class="sidebar">
            <h3>Configuration Filters</h3>
            <label>Topology:</label> <select id="selTopo" onchange="updateView()"></select>
            <label>Dimension:</label> <select id="selDim" onchange="updateView()"></select>
            <label>Traffic:</label> <select id="selTraffic" onchange="updateView()"></select>
            <label>Routing:</label> <select id="selRouting" onchange="updateView()"></select>
            <label>VCs:</label> <select id="selVCs" onchange="updateView()"></select>
        </div>

        <!-- Charts and Tables -->
        <div class="main-content">
            <div class="card">
                <h3>Latency Comparison (vs. Injection Rate)</h3>
                <div class="chart-container">
                    <canvas id="latencyChart"></canvas>
                </div>
            </div>

            <div class="card">
                <h3>Throughput Comparison (vs. Injection Rate)</h3>
                <div class="chart-container">
                    <canvas id="throughputChart"></canvas>
                </div>
            </div>

            <div class="card">
                <h3>Error Analysis (Relative to BookSim)</h3>
                <table id="errorTable">
                    <thead>
                        <tr>
                            <th>Model</th>
                            <th>Zero-load Latency</th>
                            <th>Error (%)</th>
                            <th>Saturation Rate</th>
                            <th>Error (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Populated by JS -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const aggregatedData = {json.dumps(js_data)};

        let latencyChartObj = null;
        let throughputChartObj = null;

        function initFilters() {{
            const topos = new Set();
            const dims = new Set();
            const traffics = new Set();
            const routings = new Set();
            const vcs = new Set();

            aggregatedData.forEach(d => {{
                topos.add(d.topology);
                dims.add(d.dim);
                traffics.add(d.traffic);
                routings.add(d.routing);
                vcs.add(d.vcs);
            }});

            const populate = (id, set) => {{
                const el = document.getElementById(id);
                el.innerHTML = '';
                Array.from(set).sort().forEach(v => {{
                    let opt = document.createElement("option");
                    opt.value = v; opt.text = v;
                    el.appendChild(opt);
                }});
            }};

            populate('selTopo', topos);
            populate('selDim', dims);
            populate('selTraffic', traffics);
            populate('selRouting', routings);
            populate('selVCs', vcs);
        }}

        function updateView() {{
            const t = document.getElementById('selTopo').value;
            const d = parseInt(document.getElementById('selDim').value);
            const tr = document.getElementById('selTraffic').value;
            const r = document.getElementById('selRouting').value;
            const v = parseInt(document.getElementById('selVCs').value);

            const record = aggregatedData.find(x => x.topology === t && x.dim === d && x.traffic === tr && x.routing === r && x.vcs === v);

            if (!record) {{
                drawCharts([], [], []);
                updateTable(null);
                return;
            }}

            drawCharts(record.models.booksim, record.models.c_model, record.models.python_md1);
            updateTable(record.models);
        }}

        function drawCharts(bs, cm, pm) {{
            const dsLat = [];
            const dsThr = [];

            if(bs && bs.length > 0) {{
                dsLat.push({{ label: 'BookSim (Golden)', data: bs.map(pt=>({{x:pt.x, y:pt.y}})), borderColor: '#2c3e50', backgroundColor: '#2c3e50', fill: false, tension: 0.1 }});
                dsThr.push({{ label: 'BookSim (Golden)', data: bs.map(pt=>({{x:pt.x, y:pt.thr}})), borderColor: '#2c3e50', backgroundColor: '#2c3e50', fill: false, tension: 0.1 }});
            }}
            if(cm && cm.length > 0) {{
                dsLat.push({{ label: 'C-Model', data: cm.map(pt=>({{x:pt.x, y:pt.y}})), borderColor: '#e74c3c', borderDash: [5,5], fill: false, tension: 0.1 }});
                dsThr.push({{ label: 'C-Model', data: cm.map(pt=>({{x:pt.x, y:pt.thr}})), borderColor: '#e74c3c', borderDash: [5,5], fill: false, tension: 0.1 }});
            }}
            if(pm && pm.length > 0) {{
                dsLat.push({{ label: 'Python M/D/1 Theory', data: pm.map(pt=>({{x:pt.x, y:pt.y}})), borderColor: '#f1c40f', borderDash: [2,2], fill: false, tension: 0.1 }});
                // M/D/1 usually doesn't output precise throughput unless we map it linearly
            }}

            if(latencyChartObj) latencyChartObj.destroy();
            latencyChartObj = new Chart(document.getElementById('latencyChart'), {{
                type: 'line', data: {{ datasets: dsLat }},
                options: {{ responsive: true, maintainAspectRatio: false, scales: {{ x: {{ type: 'linear', title: {{ display: true, text: 'Injection Rate' }} }}, y: {{ title: {{ display: true, text: 'Latency (cycles)' }} }} }} }}
            }});

            if(throughputChartObj) throughputChartObj.destroy();
            throughputChartObj = new Chart(document.getElementById('throughputChart'), {{
                type: 'line', data: {{ datasets: dsThr }},
                options: {{ responsive: true, maintainAspectRatio: false, scales: {{ x: {{ type: 'linear', title: {{ display: true, text: 'Injection Rate' }} }}, y: {{ title: {{ display: true, text: 'Throughput (pkts/cycle)' }} }} }} }}
            }});
        }}

        function getMetrics(curve) {{
            if (!curve || curve.length === 0) return {{ zl: null, sat: null }};
            // Zero-load is the first point (lowest rate)
            const zl = curve[0].y;
            // Saturation rate is the max rate before inf
            const sat = Math.max(...curve.map(pt => pt.x));
            return {{ zl, sat }};
        }}

        function formatErr(val) {{
            if (val === null || isNaN(val)) return "N/A";
            const s = val > 0 ? "+" : "";
            const cls = Math.abs(val) <= 15 ? "err-good" : "err-bad"; // 15% margin
            return `<span class="${{cls}}">${{s}}${{val.toFixed(2)}}%</span>`;
        }}

        function updateTable(models) {{
            const tbody = document.querySelector('#errorTable tbody');
            tbody.innerHTML = '';
            if(!models || (!models.booksim || models.booksim.length === 0)) return;

            const bsM = getMetrics(models.booksim);
            const cmM = getMetrics(models.c_model);
            const pmM = getMetrics(models.python_md1);

            const addRow = (name, m) => {{
                let zl_err = (m.zl && bsM.zl) ? ((m.zl - bsM.zl) / bsM.zl * 100) : null;
                let sat_err = (m.sat && bsM.sat) ? ((m.sat - bsM.sat) / bsM.sat * 100) : null;

                let row = `<tr>
                    <td>${{name}}</td>
                    <td>${{m.zl ? m.zl.toFixed(2) : 'N/A'}}</td>
                    <td>${{name === 'BookSim (Golden)' ? '-' : formatErr(zl_err)}}</td>
                    <td>${{m.sat ? m.sat.toFixed(3) : 'N/A'}}</td>
                    <td>${{name === 'BookSim (Golden)' ? '-' : formatErr(sat_err)}}</td>
                </tr>`;
                tbody.innerHTML += row;
            }};

            addRow('BookSim (Golden)', bsM);
            if (models.c_model && models.c_model.length > 0) addRow('C-Model', cmM);
            if (models.python_md1 && models.python_md1.length > 0) addRow('Python M/D/1 Theory', pmM);
        }}

        initFilters();
        updateView();
    </script>
</body>
</html>
"""


    return html

if __name__ == "__main__":
    js_data = generate_cmp_dashboard()
    out_path = os.path.join(get_base_metrics_path(), "multi_model_cmp.html")
    with open(out_path, "w", encoding='utf-8') as f:
        f.write(generate_html(js_data))
    print(f"Multi-Model Comparison Dashboard saved to {out_path}")
