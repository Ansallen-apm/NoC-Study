from dse_tools.html_gen.lib import load_json
import sys
import os
import json
import numpy as np
from scipy.optimize import curve_fit

def queue_delay_func(rate, base, max_rate, scaling):
    """
    非線性延遲曲線擬合公式：
    L(rate) = Base + scaling * (rate / (max_rate - rate))
    當 rate -> max_rate 時，延遲趨向無限大。
    """
    # 避免除以零或負數產生錯誤
    y = np.full_like(rate, np.inf, dtype=float)
    valid = rate < max_rate
    y[valid] = base + scaling * (rate[valid] / (max_rate - rate[valid]))
    return y

def main():
    print("Generating Advanced Theory (Phase 1.5) Report...")

    # Load BookSim Micro Metrics Results
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "micro_metrics_results.json"), 'r') as f:
            micro_data = json.load(f)
    except FileNotFoundError:
        print("Error: micro_metrics_results.json not found.")
        return

    # Extract rates and latencies for fitting
    rates = []
    lats = []

    for pt in micro_data:
        if pt['latency'] != float('inf'):
            rates.append(pt['rate'])
            lats.append(pt['latency'])

    rates = np.array(rates)
    lats = np.array(lats)

    if len(rates) < 3:
        print("Not enough valid data points for curve fitting.")
        return

    # Fit the delay curve
    # Initial guess: base = min_lat, max_rate = slightly above max valid rate, scaling = 1.0
    p0 = [min(lats), max(rates) + 0.05, 1.0]
    # Bounds: base > 0, max_rate > max(rates), scaling > 0
    bounds = ([0, max(rates), 0], [np.inf, 1.0, np.inf])

    popt, _ = curve_fit(queue_delay_func, rates, lats, p0=p0, bounds=bounds)
    base_fit, max_rate_fit, scaling_fit = popt

    print(f"Curve Fitting Results:")
    print(f"  Base Latency: {base_fit:.4f}")
    print(f"  Estimated Max Rate: {max_rate_fit:.4f}")
    print(f"  Queue Scaling Factor: {scaling_fit:.4f}")

    # Generate HTML content
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Phase 1.5 Advanced Theory Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .container {{ max-width: 1000px; margin: auto; }}
        .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Phase 1.5: Advanced Micro-Metrics & Queueing Theory Verification</h1>

        <div class="card">
            <h2>1. Queueing Theory Curve Fitting</h2>
            <p><strong>Fitted Model:</strong> L = Base + Scaling * [ Rate / (Max_Rate - Rate) ]</p>
            <ul>
                <li><strong>Base Latency (Zero-load):</strong> {base_fit:.4f} cycles</li>
                <li><strong>Estimated Saturation (Max Rate):</strong> {max_rate_fit:.4f} flits/cycle/node</li>
                <li><strong>Scaling Factor:</strong> {scaling_fit:.4f}</li>
            </ul>
            <canvas id="delayChart" height="100"></canvas>
        </div>

        <div class="card">
            <h2>2. Variance and Buffer Occupancy (Markov Chain & BookSim)</h2>
            <table border="1" width="100%" style="border-collapse: collapse; text-align: center;">
                <tr>
                    <th>Injection Rate</th>
                    <th>BookSim Avg Latency</th>
                    <th>BookSim Max Latency</th>
                    <th>BookSim Latency Variance</th>
                    <th>Avg Buffer Writes (Per Port)</th>
                </tr>
"""
    for pt in micro_data:
        lat_str = f"{pt['latency']:.2f}" if pt['latency'] != float('inf') else "Saturation"
        html += f"""
                <tr>
                    <td>{pt['rate']:.3f}</td>
                    <td>{lat_str}</td>
                    <td>{pt['max_latency']}</td>
                    <td>{pt['variance']:.2f}</td>
                    <td>{pt.get('avg_buffer_writes', 0.0):.2f}</td>
                </tr>
"""

    html += f"""
            </table>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('delayChart').getContext('2d');
        const dataRates = {rates.tolist()};
        const dataLats = {lats.tolist()};

        // Generate fitted curve data
        const fitRates = [];
        const fitLats = [];
        for(let r=0.01; r<={max_rate_fit - 0.01:.4f}; r+=0.01) {{
            fitRates.push(r);
            const l = {base_fit} + {scaling_fit} * (r / ({max_rate_fit} - r));
            fitLats.push(l);
        }}

        new Chart(ctx, {{
            type: 'line',
            data: {{
                datasets: [
                    {{
                        label: 'BookSim Empirical Data',
                        data: dataRates.map((r, i) => ({{x: r, y: dataLats[i]}})),
                        borderColor: 'blue',
                        backgroundColor: 'blue',
                        showLine: false,
                        pointRadius: 5
                    }},
                    {{
                        label: 'Queueing Theory Fit',
                        data: fitRates.map((r, i) => ({{x: r, y: fitLats[i]}})),
                        borderColor: 'red',
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0
                    }}
                ]
            }},
            options: {{
                scales: {{
                    x: {{ type: 'linear', title: {{ display: true, text: 'Injection Rate' }} }},
                    y: {{ title: {{ display: true, text: 'Latency' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "html", "advanced_micro_metrics_report.html")
    with open(out_path, "w") as f:
        f.write(html)

    print(f"Report saved to {out_path}")

if __name__ == "__main__":
    main()
