import os
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.html_utils import render_template, save_html

import yaml
import csv

def generate_html():
    results_file = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'custom_workload', 'data', 'custom_workload_results.json')
    config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'custom_workload.yaml')

    if not os.path.exists(results_file):
        print(f"Error: {results_file} not found.")
        return

    with open(results_file, 'r') as f:
        results = json.load(f)

    injection_rates = []
    matrix = []

    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            injection_rates = config.get('simulation', {}).get('injection_rate', [])
            matrix_file_rel = config.get('simulation', {}).get('custom_matrix_file', '')

            if matrix_file_rel:
                matrix_file = os.path.join(os.path.dirname(__file__), '..', '..', matrix_file_rel)
                if os.path.exists(matrix_file):
                    with open(matrix_file, 'r') as mf:
                        reader = csv.reader(mf)
                        next(reader) # skip header
                        for row in reader:
                            matrix.append([float(x) for x in row])

    html = render_template('custom_workload_report.html', base_path="../../../",  results=results, injection_rates=injection_rates, matrix=matrix, chart_js=True)

    html_path = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'custom_workload', 'html', 'custom_workload_report.html')
    save_html(html, html_path)
    print(f"HTML Report generated at {html_path}")

if __name__ == "__main__":
    generate_html()
