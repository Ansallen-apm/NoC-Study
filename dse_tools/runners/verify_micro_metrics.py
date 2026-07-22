import sys
import os
import subprocess
import re
import json
import tempfile
import yaml

BOOKSIM_EXEC = os.path.join(os.path.dirname(__file__), '..', '..', 'third_party', 'booksim', 'src', 'booksim')

def run_booksim_micro(topo, dim, vcs, p_size, b_size, rate):
    cfg_str = f"""
topology = {topo};
k = {dim};
n = 2;
routing_function = dim_order;
traffic = uniform;
injection_rate = {rate};
sim_count = 1;
num_vcs = {vcs};
vc_buf_size = {b_size};
packet_size = {p_size};
print_activity = 1;
sample_period = 5000;
sim_type = latency;
measure_stats = 1;
print_csv_results = 1;
stats_out = -;
"""
    if topo == 'ring':
        cfg_str = cfg_str.replace("topology = ring;", "topology = torus;\nn = 1;")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
        f.write(cfg_str)
        temp_path = f.name

    lat = float('inf')
    var = 0.0
    max_lat = 0
    avg_buffer_occupancy = 0.0
    buffer_full_count = 0

    try:
        result = subprocess.run([BOOKSIM_EXEC, temp_path], capture_output=True, text=True, check=False)
        out = result.stdout

        # BookSim 遇到未正確定義 config 可能會失敗退出
        if result.returncode != 0 and not out.strip():
            print(f"BookSim Error Code {result.returncode}:\n{result.stderr}")
            return float('inf'), 0.0, 0

        # 檢查 BookSim 是否成功結束
        if "DEADLOCK" in out:
            return float('inf'), 0.0, 0

        # 處理 BookSim 預設的 output 格式
        for line in out.split('\n'):
            # Latency parsing (包含最大與最小值解析)
            # Booksim 輸出範例:
            # Packet latency average = 24.1907 (1 samples)
            # 但在多 run 的時候會有:
            # 	maximum = 0.052 (1 samples)
            m_lat = re.search(r'Packet latency average = ([\d\.]+)', line)
            if m_lat:
                lat = float(m_lat.group(1))

        # 我們擷取最後的延遲分佈歷史紀錄 (plat_hist) 來精確計算 Variance
        # 尋找 plat_hist(1,:) = [ ... ]
        m_hist = re.search(r'plat_hist\(\d+,:\)\s*=\s*\[(.*?)\]', out)
        if m_hist:
            hist_str = m_hist.group(1).strip()
            # The output array can contain spaces and numbers, so we just split by space and filter digits
            counts = [int(x) for x in hist_str.split() if x.strip().isdigit()]

            total_pkts = sum(counts)
            if total_pkts > 0:
                # counts 的 index 對應 delay
                weighted_sum = sum(i * count for i, count in enumerate(counts))
                avg_calc = weighted_sum / total_pkts

                # 計算 variance = E[X^2] - E[X]^2
                weighted_sq_sum = sum((i ** 2) * count for i, count in enumerate(counts))
                var = (weighted_sq_sum / total_pkts) - (avg_calc ** 2)

                # 找到最後一個不為 0 的 index 作為 max_latency
                for i in range(len(counts)-1, -1, -1):
                    if counts[i] > 0:
                        max_lat = i
                        break

        # 解析 Buffer Occupancy
        # BookSim 的 bufferMonitor 輸出: [ 0 ] Type=0:(R#4432,W#4432)
        total_reads = 0
        total_writes = 0
        port_count = 0

        for line in out.split('\n'):
            if "Type=" in line and "R#" in line and "W#" in line:
                m_rw = re.search(r'\(R#(\d+),W#(\d+)\)', line)
                if m_rw:
                    total_reads += int(m_rw.group(1))
                    total_writes += int(m_rw.group(2))
                    port_count += 1

        # 簡單估算平均每個 port 在整個模擬週期中的寫入量
        if port_count > 0:
            avg_buffer_occupancy = float(total_writes) / port_count

    finally:
        os.remove(temp_path)

    return lat, var, max_lat, avg_buffer_occupancy

def main():
    print("Gathering micro metrics...")

    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'NoC_config.yaml')
    with open(config_path, 'r') as f:
        master_config = yaml.safe_load(f)

    topo = master_config.get('architecture', {}).get('topology', 'mesh')
    dim = master_config.get('architecture', {}).get('width', 4)
    vcs = master_config.get('architecture', {}).get('num_vcs', 2)
    b_size = master_config.get('architecture', {}).get('buffer_size', 8)
    p_size = master_config.get('architecture', {}).get('packet_size', 1)

    rates = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4]
    results = []

    for r in rates:
        lat, var, max_lat, avg_buf = run_booksim_micro(topo, dim, vcs, p_size, b_size, r)
        results.append({
            "rate": r,
            "latency": lat,
            "variance": var,
            "max_latency": max_lat,
            "avg_buffer_writes": avg_buf
        })
        print(f"Rate: {r:.2f} | Lat: {lat:.2f} | Var: {var:.2f} | Max Lat: {max_lat} | Avg Buf: {avg_buf:.2f}")

    out_file = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'uniform_dse', 'data', 'micro_metrics_results.json')
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    main()
