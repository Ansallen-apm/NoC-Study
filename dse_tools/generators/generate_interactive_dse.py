import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.html_utils import render_template, save_html

def generate_interactive_html():
    unified_data = []

    # 1. 讀取 verification_results.json
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "cross_verification", "data", "verification_results.json")):
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "cross_verification", "data", "verification_results.json"), 'r', encoding='utf-8') as f:
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

    # 2. 讀取 report_full_booksim_ring.json
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "report_full_booksim_ring.json")):
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "report_full_booksim_ring.json"), 'r', encoding='utf-8') as f:
                r_results = json.load(f)
        except Exception as e:
            print(f"錯誤：讀取 report_full_booksim_ring.json 失敗 ({e})。")
            r_results = {}

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

    options = {
        "topology": sorted(list(set(r['topology'] for r in unified_data))),
        "routing": sorted(list(set(r['routing'] for r in unified_data))),
        "traffic": sorted(list(set(r['traffic'] for r in unified_data))),
        "packet_size": sorted(list(set(r['packet_size'] for r in unified_data))),
        "buffer_size": sorted(list(set(r['buffer_size'] for r in unified_data))),
        "vcs": sorted(list(set(r['vcs'] for r in unified_data)))
    }

    html = render_template('interactive_dse.html', base_path="../../../",  chart_data=unified_data, options_data=options, chart_js=True)

    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "html", "interactive_dse_trends.html")
    save_html(html, output_path)
    print(f"互動式 HTML 報告已產生：{output_path}")

if __name__ == "__main__":
    generate_interactive_html()
