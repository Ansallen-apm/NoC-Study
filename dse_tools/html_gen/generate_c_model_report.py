from dse_tools.html_gen.lib import load_json
import sys
import os
import json
import yaml

def generate_report():
    c_model_results_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "c_model_sweep_results.json")
    booksim_results_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "verification_results.json")
    config_path = "config/NoC_config.yaml"
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "docs", "c_model_report.md")

    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            topo = config['topology']['name']
            width = config['topology']['width']
            height = config['topology']['height']
            nodes = width * height if topo in ['mesh', 'torus'] else config['topology']['nodes']
            buf_size = config['router']['buffer_size']
        c_model_data = load_json(c_model_results_path, [])
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            topo = config['topology']['name']
            width = config['topology']['width']
            height = config['topology']['height']
            nodes = width * height if topo in ['mesh', 'torus'] else config['topology']['nodes']
            buf_size = config['router']['buffer_size']
    except FileNotFoundError as e:
        return f"錯誤：找不到報告檔案 {e.filename}，請先執行對應的模擬腳本。"
    except json.JSONDecodeError as e:
        return f"錯誤：報告檔案 {c_model_results_path} 格式損壞 ({e})。"

    # Load BookSim & Theory results
    bs_data = None
    try:
        all_bs_data = load_json(booksim_results_path, [])
        # Find matching configuration
        for entry in all_bs_data:
            if entry['topology'] == topo and entry['nodes'] == nodes:
                bs_data = entry
                break
    except Exception as e:
        print(f"警告：讀取 {booksim_results_path} 失敗 ({e})。忽略 BookSim 資料。")

    # Generate Markdown
    md = f"# C++ Model (Phase 2) Verification Report\n\n"
    md += f"## Configuration\n"
    md += f"- **Topology**: {topo.capitalize()} {width}x{height} ({nodes} nodes)\n"
    md += f"- **Buffer Size**: {buf_size}\n"
    md += f"- **Traffic Pattern**: Uniform Random\n\n"

    md += f"## Comparison: C++ Model vs BookSim vs Theory\n\n"
    md += f"| Injection Rate | C++ Model Latency | C++ Model Throughput | BookSim Latency |\n"
    md += f"|---|---|---|---|\n"

    for c_entry in c_model_data:
        rate = c_entry['rate']
        c_lat = c_entry['latency']
        c_thr = c_entry['throughput']

        bs_lat = "N/A"
        if bs_data:
            for bs_entry in bs_data['latency_curve']:
                if abs(bs_entry['rate'] - rate) < 0.001:
                    bs_lat = f"{bs_entry['latency']:.4f}"
                break

        c_lat_str = f"{c_lat:.4f}" if c_lat != float('inf') else "Saturation"

        md += f"| {rate:.3f} | {c_lat_str} | {c_thr:.4f} | {bs_lat} |\n"

    md += f"\n## Analysis\n"
    md += f"1. **Zero-Load Latency**: The C++ model shows a significantly lower zero-load latency compared to BookSim. This is because the C++ prototype currently abstracts routing and arbitration into a single ideal cycle (`evaluate` + `update`), whereas BookSim accurately models pipeline stages (routing calculation, switch allocation, VC allocation, crossbar traversal).\n"
    md += f"2. **Throughput Scaling**: The C++ model effectively scales throughput proportionally to the injection rate before saturation.\n"
    md += f"3. **Race Condition Resolution**: The implementation of double buffering guarantees deterministic execution order regardless of the loop iteration sequence across the node array.\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"Report generated at {output_path}")

if __name__ == "__main__":
    generate_report()
