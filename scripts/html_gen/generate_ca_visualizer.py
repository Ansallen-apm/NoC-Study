import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import html_gen.lib.html_utils as html_utils

def generate_visualizer():
    trace_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports", "huawei_c_model", "data", "ca_trace.json")

    if not os.path.exists(trace_path):
        print(f"Error: Could not find {trace_path}")
        return

    try:
        with open(trace_path, 'r') as f:
            trace_data = json.load(f)
    except Exception as e:
        print(f"Error reading trace data: {e}")
        return

    html_content = html_utils.render_template('ca_visualizer.html', base_path="../../../",  trace_data=trace_data, chart_js=False, datatables=False)

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports", "huawei_c_model", "html", "ca_visualizer.html")
    html_utils.save_html(html_content, output_path)

    print(f"CA Visualizer HTML generated successfully at {output_path}")

if __name__ == "__main__":
    generate_visualizer()
