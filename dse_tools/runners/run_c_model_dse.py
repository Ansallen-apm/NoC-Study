import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
import subprocess
import re
from multiprocessing import Pool
import random

def generate_trace(num_nodes, injection_rate, sim_cycles, trace_file):
    with open(trace_file, 'w') as f:
        for cycle in range(sim_cycles):
            for src in range(num_nodes):
                if random.random() < injection_rate:
                    dst = random.randint(0, num_nodes - 1)
                    while dst == src:
                        dst = random.randint(0, num_nodes - 1)
                    payload = random.randint(100, 999)
                    f.write(f"{src} {dst} {payload} {cycle}\n")

def run_single_simulation(args):
    rate, num_nodes, sim_cycles, config_path, c_model_executable = args

    trace_path = f"temp_trace_{rate}.txt"
    generate_trace(num_nodes, rate, sim_cycles, trace_path)

    latency = float('inf')
    throughput = 0.0
    try:
        result = subprocess.run([c_model_executable, config_path, trace_path], capture_output=True, text=True, timeout=30)
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

        # Check if saturation caused simulation to fail to finish all packets
        if "Pending Packets:" in output:
            latency = float('inf') # Consider it saturated/deadlocked if packets get stuck

    except subprocess.TimeoutExpired:
        latency = float('inf')
    except Exception as e:
        latency = float('inf')
    finally:
        if os.path.exists(trace_path):
            os.remove(trace_path)

    return rate, latency, throughput

def main():
    print("啟動 NoC DSE 階段 2：C++ 功能模型掃描驗證...")

    config_path = "config/NoC_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        master_config = yaml.safe_load(f)

    width = master_config.get('architecture', {}).get('width', 4)
    height = master_config.get('architecture', {}).get('height', 4)
    num_nodes = width * height
    sim_cycles = master_config.get('simulation', {}).get('sim_cycles', 5000)

    sweep_range = master_config.get('simulation', {}).get('sweep_range', {'start': 0.05, 'end': 0.50, 'step': 0.05})
    start = int(sweep_range.get('start', 0.05) * 1000)
    end = int(sweep_range.get('end', 0.50) * 1000)
    step = int(sweep_range.get('step', 0.05) * 1000)

    injection_rates = [float(i) / 1000.0 for i in range(start, end + step, step)]

    c_model_executable = "../noc_c_model/noc_sim"
    if not os.path.exists(c_model_executable):
        print(f"錯誤：找不到 C++ 執行檔於 {c_model_executable}，請先編譯。")
        return

    print(f"開始平行模擬，共 {len(injection_rates)} 個注入率點...")
    pool_args = [(rate, num_nodes, sim_cycles, config_path, c_model_executable) for rate in injection_rates]

    results = []
    with Pool(processes=multiprocessing.cpu_count()) as pool:
        sim_results = pool.map(run_single_simulation, pool_args)

    for rate, lat, thr in sim_results:
        results.append({"rate": rate, "latency": lat, "throughput": thr})
        if lat != float('inf'):
            print(f"  Rate: {rate:.3f} -> 平均延遲: {lat:.4f} cycles, 吞吐量: {thr:.4f} pkts/cycle")
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
