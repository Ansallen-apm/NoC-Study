import sys
import os
import yaml
import json
import multiprocessing
import subprocess
import re
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
from core.metrics import calculate_average_hop_count, analyze_channel_load, calculate_channel_count, calculate_bisection_bandwidth

BOOKSIM_EXEC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'third_party', 'booksim', 'src', 'booksim')

def get_theoretical_metrics(topo_type, dim):
    if topo_type == 'mesh':
        graph = generate_mesh_topology(dim, dim)
    elif topo_type == 'torus':
        graph = generate_torus_topology(dim, dim)
    elif topo_type == 'ring':
        graph = generate_ring_topology(dim)
    else:
        return None, None, None, None, None, None

    channel_count = calculate_channel_count(graph)
    bisection_bw = calculate_bisection_bandwidth(graph, channel_bandwidth_bits=32)
    avg_hops = calculate_average_hop_count(graph)

    load_analysis = analyze_channel_load(graph, routing_algorithm='xy')
    max_load = load_analysis['max_load']
    edge_loads = load_analysis.get('all_edge_loads', {})

    theo_max_rate = 1.0 / max_load if max_load > 0 else 1.0

    return channel_count, bisection_bw, max_load, edge_loads, avg_hops, theo_max_rate

def generate_bs_config(topo_type, dim, vcs, p_size, b_size, rate):
    if topo_type == 'mesh':
        topo_str = f"topology = mesh;\nk = {dim};\nn = 2;"
    elif topo_type == 'torus':
        topo_str = f"topology = torus;\nk = {dim};\nn = 2;"
    elif topo_type == 'ring':
        topo_str = f"topology = torus;\nk = {dim};\nn = 1;"
    else:
        topo_str = ""

    return f"""
{topo_str}
routing_function = dim_order;
num_vcs = {vcs};
vc_buf_size = {b_size};
traffic = uniform;
injection_rate = {rate};
packet_size = {p_size};
sim_type = latency;
warmup_periods = 3;
max_samples = 5;
sample_period = 500;
vc_allocator = islip;
sw_allocator = islip;
alloc_iters = 1;
credit_delay = 1;
routing_delay = 1;
"""

def run_booksim_single(config_str, filename):
    with open(filename, 'w') as f:
        f.write(config_str)

    latency = float('inf')
    try:
        result = subprocess.run([BOOKSIM_EXEC, filename], capture_output=True, text=True, check=False)
        for line in result.stdout.split('\n'):
            match = re.search(r'Packet latency average = ([\d\.]+)', line)
            if match:
                latency = float(match.group(1))

        if "DEADLOCK" in result.stdout or "Error" in result.stderr:
            latency = float('inf')

    except Exception as e:
        latency = float('inf')
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    return latency

def run_task(task):
    task_id, topo_type, dim, vcs, p_size, b_size = task

    channel_count, bisection_bw, max_load, edge_loads, avg_hops, theo_max_rate = get_theoretical_metrics(topo_type, dim)

    rates_to_test = [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    latency_curve = []
    zero_lat = None
    actual_sat_rate = 0.0
    is_saturated = False

    for r in rates_to_test:
        if is_saturated:
            break

        cfg_str = generate_bs_config(topo_type, dim, vcs, p_size, b_size, r)
        lat = run_booksim_single(cfg_str, f"temp_run_{task_id}.txt")

        if r == 0.01:
            zero_lat = lat

        latency_curve.append({"rate": r, "latency": lat})

        if lat == float('inf') or (zero_lat and lat > (zero_lat * 5)):
            is_saturated = True
        else:
            actual_sat_rate = r

    nodes = dim * dim if topo_type in ['mesh', 'torus'] else dim
    total_throughput = nodes * actual_sat_rate

    routing_algo = 'dim_order' if topo_type in ['torus', 'ring'] else 'xy'

    return {
        "topology": topo_type,
        "dim": dim,
        "nodes": nodes,
        "routing": routing_algo,
        "traffic": "uniform",
        "packet_size": p_size,
        "buffer_size": b_size,
        "vcs": vcs,
        "theory_channel_count": channel_count,
        "theory_bisection_bw": bisection_bw,
        "theory_max_load": max_load,
        "theory_edge_loads": edge_loads,
        "theory_avg_hops": avg_hops,
        "booksim_zero_load_lat": zero_lat if zero_lat else float('inf'),
        "theory_max_rate": theo_max_rate,
        "booksim_actual_sat_rate": actual_sat_rate,
        "booksim_total_throughput": total_throughput,
        "latency_curve": latency_curve
    }

def main():
    print("啟動 BookSim vs Python 理論 交叉驗證與相關性分析...")

    if not os.path.exists(BOOKSIM_EXEC):
        print(f"錯誤：找不到 BookSim 執行檔 {BOOKSIM_EXEC}")
        return

    with open('dse_tools/config/verification_sweep.yaml', 'r') as f:
        sweep_cfg = yaml.safe_load(f)

    common = sweep_cfg.get('common', {})
    p_size = common.get('packet_size', 1)
    b_size = common.get('buffer_size', 8)

    tasks = []
    task_id = 0
    for group in sweep_cfg.get('sweep', []):
        topo = group['topology']
        vcs = group['vcs']
        for dim in group['dimensions']:
            tasks.append((task_id, topo, dim, vcs, p_size, b_size))
            task_id += 1

    print(f"產生了 {len(tasks)} 組拓撲設定，開始平行驗證...")

    results = []
    num_cores = max(1, multiprocessing.cpu_count())
    with multiprocessing.Pool(processes=num_cores) as pool:
        for i, res in enumerate(pool.imap_unordered(run_task, tasks)):
            results.append(res)
            print(f"進度: {i+1}/{len(tasks)} 完成.")

    os.makedirs('dse_tools/report', exist_ok=True)
    with open('dse_tools/report/verification_results.json', 'w') as f:
        json.dump(results, f, indent=4)

    calc_and_plot(results)

def calc_and_plot(results):
    print("Skipping correlation plot generation for now to speed up the process...")

if __name__ == "__main__":
    main()
