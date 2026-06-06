import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
import subprocess
import re
from multiprocessing import Pool
import random
from core.metrics import get_traffic_destinations

def generate_trace(num_nodes, injection_rate, sim_cycles, trace_file, pattern, width, height):
    with open(trace_file, 'w') as f:
        for cycle in range(sim_cycles):
            for src in range(num_nodes):
                if random.random() < injection_rate:
                    # Get probability distribution for this source under the specified pattern
                    dests = get_traffic_destinations(src, num_nodes, pattern, width, height)

                    if not dests: continue

                    # Choose destination based on probabilities
                    r = random.random()
                    cumulative = 0.0
                    chosen_dst = -1
                    for dst, prob in dests:
                        cumulative += prob
                        if r <= cumulative:
                            chosen_dst = dst
                            break

                    # Fallback in case of rounding errors
                    if chosen_dst == -1:
                        chosen_dst = dests[-1][0]

                    if chosen_dst != src:
                        payload = random.randint(100, 999)
                        f.write(f"{src} {chosen_dst} {payload} {cycle}\n")

def run_single_simulation(args):
    rate, num_nodes, sim_cycles, config_path, c_model_executable, pattern, width, height = args

    trace_path = f"temp_trace_{rate}.txt"
    generate_trace(num_nodes, rate, sim_cycles, trace_path, pattern, width, height)

    latency = float('inf')
    throughput = 0.0
    bw_gbps = 0.0
    router_stats = None
    try:
        # Run C++ simulator. It outputs 'router_stats.json' in the current working directory.
        # To prevent race conditions from parallel executions overriding router_stats.json,
        # we run it in a temporary directory or capture it securely.
        import tempfile
        import shutil
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_config_path = os.path.abspath(config_path)
            temp_trace_path = os.path.join(tmpdir, "trace.txt")
            shutil.copy(trace_path, temp_trace_path)

            result = subprocess.run([os.path.abspath(c_model_executable), temp_config_path, temp_trace_path],
                                    capture_output=True, text=True, timeout=30, cwd=tmpdir)
            output = result.stdout

            # 解析輸出
            for line in output.split('\n'):
                if "Average Latency:" in line:
                    match = re.search(r"Average Latency:\s*([0-9.]+)", line)
                    if match:
                        latency = float(match.group(1))
                if "Total Throughput:" in line:
                    match = re.search(r"Total Throughput:\s*([0-9.]+)", line)
                    if match:
                        throughput = float(match.group(1))
                if "Total Bandwidth:" in line:
                    match = re.search(r"Total Bandwidth:\s*([0-9.]+)", line)
                    if match:
                        bw_gbps = float(match.group(1))

            # Load the generated JSON stats file
            stats_file = os.path.join(tmpdir, "router_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    router_stats = json.load(f)

            is_deadlock = False
            if router_stats and router_stats.get('system_metrics', {}).get('is_deadlock', False):
                is_deadlock = True

            # Check if saturation caused simulation to fail to finish all packets
            if "Pending Packets:" in output or is_deadlock:
                latency = float('inf') # Consider it saturated/deadlocked if packets get stuck

    except subprocess.TimeoutExpired:
        latency = float('inf')
    except Exception as e:
        latency = float('inf')
    finally:
        if os.path.exists(trace_path):
            os.remove(trace_path)

    return rate, latency, throughput, bw_gbps, router_stats

def main():
    print("啟動 NoC DSE 階段 2：C++ 功能模型掃描驗證...")

    config_path = "dse_tools/config/NoC_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        master_config = yaml.safe_load(f)

    topo = master_config.get('architecture', {}).get('topology', 'mesh')
    width = master_config.get('architecture', {}).get('width', 4)
    height = master_config.get('architecture', {}).get('height', 4)
    if topo == 'ring':
        num_nodes = width
        height = 1
    else:
        num_nodes = width * height

    sim_cycles = master_config.get('simulation', {}).get('sim_cycles', 5000)
    traffic_pattern = master_config.get('simulation', {}).get('traffic_pattern', 'uniform')

    sweep_range = master_config.get('simulation', {}).get('sweep_range', {'start': 0.05, 'end': 0.50, 'step': 0.05})
    start = int(sweep_range.get('start', 0.05) * 1000)
    end = int(sweep_range.get('end', 0.50) * 1000)
    step = int(sweep_range.get('step', 0.05) * 1000)

    injection_rates = [float(i) / 1000.0 for i in range(start, end + step, step)]

    c_model_executable = "noc_c_model/noc_sim"
    if not os.path.exists(c_model_executable):
        print(f"錯誤：找不到 C++ 執行檔於 {c_model_executable}，請先編譯。")
        return

    print(f"開始平行模擬 (Pattern: {traffic_pattern})，共 {len(injection_rates)} 個注入率點...")
    pool_args = [(rate, num_nodes, sim_cycles, config_path, c_model_executable, traffic_pattern, width, height) for rate in injection_rates]

    results = []
    with Pool(processes=multiprocessing.cpu_count()) as pool:
        sim_results = pool.map(run_single_simulation, pool_args)

    for rate, lat, thr, bw, stats in sim_results:
        is_deadlock = False
        if stats and stats.get('system_metrics', {}).get('is_deadlock', False):
            is_deadlock = True

        results.append({"rate": rate, "latency": lat, "throughput": thr, "bandwidth_gbps": bw, "router_stats": stats, "is_deadlock": is_deadlock})
        if lat != float('inf'):
            print(f"  Rate: {rate:.3f} -> 平均延遲: {lat:.4f} cycles, 頻寬: {bw:.2f} GB/s")
        else:
            if is_deadlock:
                print(f"  Rate: {rate:.3f} -> 死結發生 (DEADLOCK DETECTED)")
            else:
                print(f"  Rate: {rate:.3f} -> 網路飽和/不穩定")

    import json
    os.makedirs("report", exist_ok=True)
    report_file = "report/c_model_sweep_results.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=4)

    print(f"結果已儲存至 {report_file}")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
