import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
import os
import subprocess
import multiprocessing
import re
import json
import numpy as np
import matplotlib.pyplot as plt

from core.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
from core.metrics import calculate_average_hop_count, analyze_channel_load, calculate_channel_count, calculate_bisection_bandwidth

BOOKSIM_EXEC = "../third_party/booksim/src/booksim"

def get_theoretical_metrics(topo_type, dim):
    """取得 Python 計算的理論指標"""
    if topo_type == 'mesh':
        graph = generate_mesh_topology(dim, dim)
    elif topo_type == 'torus':
        graph = generate_torus_topology(dim, dim)
    elif topo_type == 'ring':
        graph = generate_ring_topology(dim)
    else:
        return None, None, None, None, None

    channel_count = calculate_channel_count(graph)
    bisection_bw = calculate_bisection_bandwidth(graph, channel_bandwidth_bits=32)
    avg_hops = calculate_average_hop_count(graph)

    # 預設 xy/dim_order
    load_analysis = analyze_channel_load(graph, routing_algorithm='xy')
    max_load = load_analysis['max_load']

    # 對於單向計數的最大負載，理論極限的推演：
    # 如果最擁擠的通道平均每個週期要承載 max_load 個封包，
    # 則節點的注入率上限為 1.0 / max_load (假設單位為 1 flit)
    theo_max_rate = 1.0 / max_load if max_load > 0 else 1.0

    return channel_count, bisection_bw, max_load, avg_hops, theo_max_rate

def generate_bs_config(topo_type, dim, vcs, p_size, b_size, rate):
    """產生單次 BookSim 設定字串"""
    # 根據不同拓撲設定參數
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

        # Check for saturation/deadlock
        if "DEADLOCK" in result.stdout or "Error" in result.stderr:
            latency = float('inf')

    except Exception as e:
        latency = float('inf')
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    return latency

def run_task(task):
    """在子行程執行的單一驗證任務"""
    task_id, topo_type, dim, vcs, p_size, b_size = task

    # 1. 計算理論值
    channel_count, bisection_bw, max_load, avg_hops, theo_max_rate = get_theoretical_metrics(topo_type, dim)

    # 2. 密集掃描所有的注入率 (Injection Rates)
    # 不再只找飽和點，而是收集一整條 Latency 曲線
    rates_to_test = [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    latency_curve = []
    zero_lat = None
    actual_sat_rate = 0.0
    is_saturated = False

    for r in rates_to_test:
        if is_saturated:
            break # 已經飽和了，後面的高負載不需要再跑

        cfg_str = generate_bs_config(topo_type, dim, vcs, p_size, b_size, r)
        lat = run_booksim_single(cfg_str, f"temp_run_{task_id}.txt")

        if r == 0.01:
            zero_lat = lat

        latency_curve.append({"rate": r, "latency": lat})

        # 判斷飽和
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
        "theory_channel_count": channel_count,
        "theory_bisection_bw": bisection_bw,
        "theory_max_load": max_load,
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

    # 讀取 Sweep Config
    with open('config/verification_sweep.yaml', 'r') as f:
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

    # 儲存 JSON
    os.makedirs('report', exist_ok=True)
    with open('report/verification_results.json', 'w') as f:
        json.dump(results, f, indent=4)

    # 數據分析與畫圖 (Correlation)
    calc_and_plot(results)

def calc_and_plot(results):
    theory_hops = []
    bs_zlat = []
    theory_rate = []
    bs_sat = []
    theory_max_load = []
    bs_sat_inv = [] # 飽和點的倒數，對應 Max Load
    theory_bisec = []
    bs_throughput = []

    for r in results:
        # 過濾掉失敗的點
        if r['booksim_zero_load_lat'] != float('inf') and r['theory_avg_hops'] is not None:
            theory_hops.append(r['theory_avg_hops'])
            bs_zlat.append(r['booksim_zero_load_lat'])
            theory_rate.append(r['theory_max_rate'])
            bs_sat.append(r['booksim_actual_sat_rate'])
            theory_max_load.append(r['theory_max_load'])
            # 若 sat rate 為 0 則給極大值，否則取倒數
            bs_sat_inv.append(1.0 / r['booksim_actual_sat_rate'] if r['booksim_actual_sat_rate'] > 0 else float('inf'))
            theory_bisec.append(r['theory_bisection_bw'])
            bs_throughput.append(r['booksim_total_throughput'])

    # 過濾有效計算範圍
    valid_inv = [i for i, x in enumerate(bs_sat_inv) if x != float('inf')]
    theory_max_load = [theory_max_load[i] for i in valid_inv]
    bs_sat_inv = [bs_sat_inv[i] for i in valid_inv]

    # 1. 繪製 Zero-Load Correlation
    plt.figure(figsize=(8, 6))
    plt.scatter(theory_hops, bs_zlat, color='blue', s=100, alpha=0.7)

    # 計算相關係數 (Pearson)
    if len(theory_hops) > 1:
        corr_hops = np.corrcoef(theory_hops, bs_zlat)[0, 1]
    else:
        corr_hops = 0.0

    # Fit line
    m, b = np.polyfit(theory_hops, bs_zlat, 1)
    plt.plot(np.array(theory_hops), m*np.array(theory_hops) + b, color='red', linestyle='--')

    plt.title(f'Zero-load Latency vs. Theory Avg Hops\nCorrelation: {corr_hops:.4f}')
    plt.xlabel('Python Theory Average Hops')
    plt.ylabel('BookSim Zero-Load Latency (cycles)')
    plt.grid(True)
    plt.savefig('report/zero_load_correlation.png')

    # 2. 繪製 Saturation Correlation
    plt.figure(figsize=(8, 6))
    plt.scatter(theory_rate, bs_sat, color='green', s=100, alpha=0.7)

    if len(theory_rate) > 1:
        corr_rate = np.corrcoef(theory_rate, bs_sat)[0, 1]
    else:
        corr_rate = 0.0

    m2, b2 = np.polyfit(theory_rate, bs_sat, 1)
    plt.plot(np.array(theory_rate), m2*np.array(theory_rate) + b2, color='red', linestyle='--')

    plt.title(f'BookSim Saturation vs. Theory Max Injection Rate\nCorrelation: {corr_rate:.4f}')
    plt.xlabel('Python Theory Max Injection Rate (proxy)')
    plt.ylabel('BookSim Actual Saturation Rate')
    plt.grid(True)
    plt.savefig('report/saturation_correlation.png')

    # 3. 繪製 Max Load Correlation
    plt.figure(figsize=(8, 6))
    plt.scatter(theory_max_load, bs_sat_inv, color='purple', s=100, alpha=0.7)
    corr_load = np.corrcoef(theory_max_load, bs_sat_inv)[0, 1] if len(theory_max_load) > 1 else 0.0
    m3, b3 = np.polyfit(theory_max_load, bs_sat_inv, 1)
    plt.plot(np.array(theory_max_load), m3*np.array(theory_max_load) + b3, color='red', linestyle='--')
    plt.title(f'BookSim Saturation (Inv) vs. Theory Max Load\nCorrelation: {corr_load:.4f}')
    plt.xlabel('Python Theory Max Channel Load')
    plt.ylabel('BookSim Saturation Rate Inverted (1 / Sat_Rate)')
    plt.grid(True)
    plt.savefig('report/max_load_correlation.png')

    # 4. 繪製 Bisection Bandwidth vs Total Throughput Correlation
    plt.figure(figsize=(8, 6))
    plt.scatter(theory_bisec, bs_throughput, color='orange', s=100, alpha=0.7)
    corr_bw = np.corrcoef(theory_bisec, bs_throughput)[0, 1] if len(theory_bisec) > 1 else 0.0
    m4, b4 = np.polyfit(theory_bisec, bs_throughput, 1)
    plt.plot(np.array(theory_bisec), m4*np.array(theory_bisec) + b4, color='red', linestyle='--')
    plt.title(f'BookSim Total Throughput vs. Theory Bisection BW\nCorrelation: {corr_bw:.4f}')
    plt.xlabel('Python Theory Bisection Bandwidth (bps)')
    plt.ylabel('BookSim Total Throughput at Saturation (packets/cycle)')
    plt.grid(True)
    plt.savefig('report/bisection_bw_correlation.png')

    print("\n=== 交叉驗證總結 ===")
    print(f"Zero-Load 延遲相關係數 (Avg Hops vs Base Latency) = {corr_hops:.4f} (預期接近 1.0)")
    print(f"網路飽和度相關係數 (Theory Max Rate vs Actual Sat Rate) = {corr_rate:.4f} (預期接近 1.0)")
    print(f"最大通道負載相關係數 (Max Load vs 1/Actual_Sat_Rate) = {corr_load:.4f} (預期接近 1.0)")
    print(f"二分頻寬相關係數 (Bisection BW vs Total Throughput) = {corr_bw:.4f} (預期高度正相關)")
    print("所有圖表已匯出至 report/ 目錄下。")

if __name__ == "__main__":
    main()
