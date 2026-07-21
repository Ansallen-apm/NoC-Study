import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.data_utils import load_json
from scripts.html_gen.lib.html_utils import render_template, save_html

def get_base_metrics_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports")

def generate_cmp_dashboard():
    reports_dir = get_base_metrics_path()

    v_results = load_json(os.path.join(reports_dir, 'cross_verification', 'data', 'verification_results.json'), [])
    c_model_data = load_json(os.path.join(reports_dir, 'c_model_eval', 'data', 'c_model_sweep_results.json'), [])
    micro_data = load_json(os.path.join(reports_dir, 'uniform_dse', 'data', 'micro_metrics_results.json'), [])

    aggregated = {}

    for r in v_results:
        topo = r.get('topology', 'mesh')
        dim = r.get('dim', 4)
        traffic = r.get('traffic', 'uniform')
        routing = r.get('routing', 'xy' if topo == 'mesh' else 'dim_order')
        vcs = r.get('vcs', 1 if topo == 'mesh' else 2)

        key = f"{topo}_{dim}_{traffic}_{routing}_{vcs}"
        if key not in aggregated:
            aggregated[key] = {
                'topology': topo,
                'dim': dim,
                'traffic': traffic,
                'routing': routing,
                'vcs': vcs,
                'models': {
                    'booksim': [],
                    'c_model': [],
                    'python_md1': []
                }
            }

        for pt in r.get('latency_curve', []):
            if pt['latency'] != float('inf'):
                thr = pt.get('throughput', 0)
                if thr == 0:
                    thr = pt['rate']
                aggregated[key]['models']['booksim'].append({'x': pt['rate'], 'y': pt['latency'], 'thr': thr})

    c_key = "mesh_4_uniform_xy_1"
    if c_key in aggregated and c_model_data:
        for pt in c_model_data:
            if pt['latency'] != float('inf'):
                aggregated[c_key]['models']['c_model'].append({'x': pt['rate'], 'y': pt['latency'], 'thr': pt.get('throughput', pt['rate'])})

    m_key = "ring_4_uniform_dim_order_2"
    if m_key in aggregated and micro_data:
        for pt in micro_data:
            if pt['latency'] != float('inf'):
                aggregated[m_key]['models']['python_md1'].append({'x': pt['rate'], 'y': pt['latency']})

    return list(aggregated.values())

def generate_html(js_data):
    return render_template('multi_model_cmp.html', base_path="../../../",  js_data=js_data, chart_js=True)

if __name__ == "__main__":
    js_data = generate_cmp_dashboard()
    out_path = os.path.join(get_base_metrics_path(), "c_model_eval", "html", "multi_model_cmp.html")
    save_html(generate_html(js_data), out_path)
    print(f"Multi-Model Comparison Dashboard saved to {out_path}")
