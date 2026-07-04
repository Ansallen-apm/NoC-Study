import sys
import os
import yaml
import subprocess
import multiprocessing
import re
import json

from noc_python_model.topology import generate_mesh_topology, generate_torus_topology
from noc_python_model.metrics import calculate_average_hop_count, analyze_channel_load

BOOKSIM_EXEC = os.path.join(os.path.dirname(__file__), '..', '..', 'third_party', 'booksim', 'src', 'booksim')

def get_theoretical_metrics(topo_type, width, height, traffic_pattern):
    """取得 Python 計算的理論指標"""
    if topo_type == 'mesh':
        graph = generate_mesh_topology(width, height)
    elif topo_type == 'torus':
        graph = generate_torus_topology(width, height)
    else:
        return None, None

    avg_hops = calculate_average_hop_count(graph, traffic_pattern=traffic_pattern)
    load_analysis = analyze_channel_load(graph, routing_algorithm='xy', traffic_pattern=traffic_pattern)
    max_load = load_analysis['max_load']

    theory_saturation_rate = 1.0 / max_load if max_load > 0 else 1.0
    return avg_hops, theory_saturation_rate

def run_booksim_single(config_path):
    """執行單一 BookSim 模擬"""
    try:
        result = subprocess.run([BOOKSIM_EXEC, config_path], capture_output=True, text=True, timeout=30)
        output = result.stdout

        latency = None
        for line in output.split('\n'):
            if "Packet latency average" in line:
                match = re.search(r"=\s*([0-9.]+)", line)
                if match:
                    latency = float(match.group(1))
                    break

        return latency if latency is not None else 10000.0  # Saturation
    except subprocess.TimeoutExpired:
        return 10000.0
    except Exception as e:
        print(f"Error running Booksim: {e}")
        return 10000.0

def process_booksim_sweep(args):
    """平行執行單一組態的所有注入率"""
    if len(args) == 7:
        config, topo, width, height, pattern, rates, num_vcs = args
    else:
        config, topo, width, height, pattern, rates = args
        num_vcs = 2
    results = {}

    # 建立暫時設定檔
    temp_config = f"temp_booksim_{topo}_{width}x{height}_{pattern}.cfg"

    # 將 topology 名稱調整為 booksim 接受的格式
    booksim_topo = config['topology']
    if booksim_topo == 'torus':
        booksim_topo = 'torus'
    else:
        booksim_topo = 'mesh'

    for rate in rates:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
            f.write(f"topology = {booksim_topo};\n")
            f.write(f"k = {width};\n")
            f.write(f"n = 2;\n")
            f.write(f"routing_function = dim_order;\n")
            f.write(f"traffic = {pattern};\n")
            f.write(f"injection_rate = {rate};\n")
            f.write(f"num_vcs = {num_vcs};\n")
            f.write(f"sim_count = 1;\n")
            temp_config_path = f.name

        try:
            latency = run_booksim_single(temp_config_path)
            results[rate] = latency

            # Early stop if saturated
            if latency >= 1000.0:
                for remaining_rate in [r for r in rates if r > rate]:
                    results[remaining_rate] = 10000.0
                break
        finally:
            if os.path.exists(temp_config_path):
                os.remove(temp_config_path)

    return topo, width, height, pattern, results

def analyze_saturation(latencies_dict, rates, threshold=100.0):
    """從延遲曲線估算飽和點"""
    base_latency = latencies_dict.get(rates[0], 0)
    for rate in rates:
        if latencies_dict[rate] > threshold:
            return rate
    return rates[-1]

def main():
    print("=== 開始流量模式交叉驗證 (Traffic Patterns Verification) ===")
    config_file = "config/traffic_pattern_sweep.yaml"
    if not os.path.exists(config_file):
        print(f"Error: 找不到設定檔 {config_file}")
        return

    with open(config_file, 'r') as f:
        sweep_cfg = yaml.safe_load(f)['sweep_parameters']

    architectures = sweep_cfg['architectures']
    patterns = sweep_cfg['traffic_patterns']

    r_cfg = sweep_cfg['injection_rate']
    rates = [round(r_cfg['start'] + i * r_cfg['step'], 3) for i in range(int((r_cfg['end'] - r_cfg['start']) / r_cfg['step']) + 1)]

    # 準備平行執行任務
    tasks = []
    num_vcs = sweep_cfg.get("common", {}).get("num_vcs", 2)
    for arch in architectures:
        topo = arch['topology']
        width = arch['width']
        height = arch['height']
        for pattern in patterns:
            tasks.append((arch, topo, width, height, pattern, rates, num_vcs))

    print(f"總共有 {len(tasks)} 組不同流量模式與拓撲配置需要掃描...")

    # 平行執行 BookSim
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(process_booksim_sweep, tasks)

    # 整合與比較結果
    final_report = []
    for topo, width, height, pattern, latencies in results:
        avg_hops, theory_sat = get_theoretical_metrics(topo, width, height, pattern)
        actual_sat = analyze_saturation(latencies, rates)
        base_latency = latencies.get(rates[0], 0)

        report_entry = {
            "topology": topo,
            "dimensions": f"{width}x{height}",
            "traffic_pattern": pattern,
            "theory_avg_hops": round(avg_hops, 4),
            "booksim_base_latency": round(base_latency, 4),
            "theory_saturation_rate": round(theory_sat, 4),
            "booksim_actual_saturation": actual_sat,
            "latency_curve": latencies
        }
        final_report.append(report_entry)

        print(f"[{topo} {width}x{height}] Pattern: {pattern:10} | Theory Sat: {theory_sat:.4f} | BookSim Sat: {actual_sat:.4f}")

    # 輸出成 JSON 檔案
    out_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "cross_verification", "data", "traffic_verification_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w') as f:
        json.dump(final_report, f, indent=4)

    print(f"驗證完成！結果已儲存至 {out_file}")

if __name__ == "__main__":
    main()
