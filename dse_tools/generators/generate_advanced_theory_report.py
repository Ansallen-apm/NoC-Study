import sys
import os
import json
import numpy as np
from scipy.optimize import curve_fit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.html_utils import render_template, save_html

def queue_delay_func(rate, base, max_rate, scaling):
    y = np.full_like(rate, np.inf, dtype=float)
    valid = rate < max_rate
    y[valid] = base + scaling * (rate[valid] / (max_rate - rate[valid]))
    return y

def main():
    print("Generating Advanced Theory (Phase 1.5) Report...")

    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "micro_metrics_results.json"), 'r') as f:
            micro_data = json.load(f)
    except FileNotFoundError:
        print("Error: micro_metrics_results.json not found.")
        return

    rates = []
    lats = []

    for pt in micro_data:
        if pt['latency'] != float('inf'):
            rates.append(pt['rate'])
            lats.append(pt['latency'])

    rates_np = np.array(rates)
    lats_np = np.array(lats)

    if len(rates_np) < 3:
        print("Not enough valid data points for curve fitting.")
        return

    p0 = [min(lats_np), max(rates_np) + 0.05, 1.0]
    bounds = ([0, max(rates_np), 0], [np.inf, 1.0, np.inf])

    popt, _ = curve_fit(queue_delay_func, rates_np, lats_np, p0=p0, bounds=bounds)
    base_fit, max_rate_fit, scaling_fit = popt

    print(f"Curve Fitting Results:")
    print(f"  Base Latency: {base_fit:.4f}")
    print(f"  Estimated Max Rate: {max_rate_fit:.4f}")
    print(f"  Queue Scaling Factor: {scaling_fit:.4f}")

    fitRates = []
    fitLats = []
    for r_val in np.arange(0.01, max_rate_fit - 0.01, 0.01):
        fitRates.append(float(r_val))
        l = base_fit + scaling_fit * (r_val / (max_rate_fit - r_val))
        fitLats.append(float(l))

    html = render_template('advanced_theory_report.html', base_path="../../../",
                           base_fit=float(base_fit),
                           max_rate_fit=float(max_rate_fit),
                           scaling_fit=float(scaling_fit),
                           micro_data=micro_data,
                           dataRates=rates,
                           dataLats=lats,
                           fitRates=fitRates,
                           fitLats=fitLats,
                           chart_js=True,
                           datatables=False,
                           inf=float('inf'))

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "html", "advanced_micro_metrics_report.html")
    save_html(html, out_path)
    print(f"Report saved to {out_path}")

if __name__ == "__main__":
    main()
