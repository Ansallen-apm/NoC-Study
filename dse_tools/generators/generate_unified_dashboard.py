import os
import sys
import json
import numpy as np
from scipy.optimize import curve_fit

# Add root directory to sys.path to access scripts/html_gen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.data_utils import load_json
from scripts.html_gen.lib.html_utils import render_template, save_html

def queue_delay_func(rate, base, max_rate, scaling):
    y = np.full_like(rate, np.inf, dtype=float)
    valid = rate < max_rate
    y[valid] = base + scaling * (rate[valid] / (max_rate - rate[valid]))
    return y

def generate_dashboard():
    # --- 1. Load Data ---
    print("Loading data...")
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "reports")

    v_results = load_json(os.path.join(reports_dir, 'cross_verification', 'data', 'verification_results.json'), [])
    c_model_data = load_json(os.path.join(reports_dir, 'c_model_eval', 'data', 'c_model_sweep_results.json'), [])
    micro_data = load_json(os.path.join(reports_dir, 'uniform_dse', 'data', 'micro_metrics_results.json'), [])

    # --- 2. Process Macro Data (Tab 1) ---
    unified_data = []
    for r in v_results:
        vcs = r.get('vcs') if 'vcs' in r else (1 if r['topology'] == 'mesh' else 2)
        routing = r.get('routing', 'xy' if r['topology'] == 'mesh' else 'dim_order')

        # Map to unified structure
        u_record = {
            'topology': r['topology'],
            'dim': r['dim'],
            'nodes': r['nodes'],
            'traffic': 'uniform',  # verification_results is uniform
            'vcs': vcs,
            'routing': routing,
            'curve': []
        }
        for pt in r.get('latency_curve', []):
            if pt['latency'] != float('inf'):
                u_record['curve'].append({'x': pt['rate'], 'y': pt['latency']})
        if u_record['curve']:
            unified_data.append(u_record)

    # --- 3. Process Micro Data (Tab 2) ---
    rates_micro = []
    lats_micro = []
    for pt in micro_data:
        if pt['latency'] != float('inf'):
            rates_micro.append(pt['rate'])
            lats_micro.append(pt['latency'])

    rates_micro = np.array(rates_micro)
    lats_micro = np.array(lats_micro)

    base_fit, max_rate_fit, scaling_fit = 0, 0, 0
    fitRates, fitLats = [], []

    if len(rates_micro) >= 3:
        p0 = [min(lats_micro), max(rates_micro) + 0.05, 1.0]
        bounds = ([0, max(rates_micro), 0], [np.inf, 1.0, np.inf])
        try:
            popt, _ = curve_fit(queue_delay_func, rates_micro, lats_micro, p0=p0, bounds=bounds)
            base_fit, max_rate_fit, scaling_fit = popt

            for r_val in np.arange(0.01, max_rate_fit, 0.01):
                fitRates.append(r_val)
                l = base_fit + scaling_fit * (r_val / (max_rate_fit - r_val))
                fitLats.append(l)
        except Exception as e:
            print(f"Curve fit failed: {e}")

    # --- 4. Process Verification Data (Tab 3) ---
    v_results_sorted = sorted(v_results, key=lambda x: (x['topology'], x['dim']))

    # --- 5. Process C-Model Data (Tab 4) ---
    c_model_points = []
    for pt in c_model_data:
        if pt['latency'] != float('inf'):
            c_model_points.append({'x': pt['rate'], 'y': pt['latency']})

    c_booksim_curve = []
    for r in v_results:
        # Match C-model default (mesh 4x4)
        if r['topology'] == 'mesh' and r['dim'] == 4:
            for pt in r.get('latency_curve', []):
                if pt['latency'] != float('inf'):
                    c_booksim_curve.append({'x': pt['rate'], 'y': pt['latency']})
            break

    # --- 6. Render Template ---
    print("Generating Unified Dashboard...")
    html = render_template('unified_dashboard.html', base_path="../../../",
                           macro_data=unified_data,
                           micro_data=micro_data,
                           base_fit=base_fit,
                           max_rate_fit=max_rate_fit,
                           scaling_fit=scaling_fit,
                           v_results_sorted=v_results_sorted,
                           fitRates=fitRates,
                           fitLats=fitLats,
                           microRates=rates_micro.tolist(),
                           microLats=lats_micro.tolist(),
                           cModelPoints=c_model_points,
                           cBooksimPoints=c_booksim_curve,
                           chart_js=True,
                           datatables=True)

    out_file = os.path.join(reports_dir, "unified_dashboard", "html", "unified_dashboard.html")
    save_html(html, out_file)
    print(f"Unified Dashboard successfully generated at {out_file}")

if __name__ == "__main__":
    generate_dashboard()
