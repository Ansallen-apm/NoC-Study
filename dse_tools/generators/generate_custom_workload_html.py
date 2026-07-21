import os
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.html_utils import render_template, save_html

def generate_html():
    results_file = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'custom_workload', 'data', 'custom_workload_results.json')
    if not os.path.exists(results_file):
        print(f"Error: {results_file} not found.")
        return

    with open(results_file, 'r') as f:
        results = json.load(f)

    html = render_template('custom_workload_report.html', base_path="../../../",  results=results, chart_js=True)

    html_path = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'custom_workload', 'html', 'custom_workload_report.html')
    save_html(html, html_path)
    print(f"HTML Report generated at {html_path}")

if __name__ == "__main__":
    generate_html()
