import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import subprocess
import multiprocessing
import re

BOOKSIM_EXEC = "../third_party/booksim/src/booksim"

def generate_config_string(width, packet_size, buffer_size, num_vcs, injection_rate):
    """
    產生 BookSim 專為 Ring 拓撲設計的設定字串。
    BookSim 的 Torus 如果 n=1，就是 Ring (但在某些版本中 1D torus 可能需要特製的 anynet 或設定)。
    一般標準作法是設 k=width, n=1。如果在 BookSim 原生有問題，我們可以退而求其次用 Torus (n=1)
    或 k=width, n=2 (Y=1) 但這不符合標準 BookSim 定義。
    BookSim 原生支援 anynet，或是使用 kncube 且 n=1。
    這裡我們使用 topology=torus, k=width, n=1。
    """
    return f"""
topology = torus;
k = {width};
n = 1;
routing_function = dim_order;
num_vcs = {num_vcs};
vc_buf_size = {buffer_size};
traffic = uniform;
injection_rate = {injection_rate};
packet_size = {packet_size};
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

def parse_booksim_output(output):
    latency = float('inf')
    is_deadlock = False

    if "DEADLOCK" in output or "deadlock" in output.lower():
        is_deadlock = True

    for line in output.split('\n'):
        match = re.search(r'Packet latency average = ([\d\.]+)', line)
        if match:
            latency = float(match.group(1))

    return latency, is_deadlock

def run_simulation(task):
    width, p_size, b_size, vcs, rate = task
    config_str = generate_config_string(width, p_size, b_size, vcs, rate)

    # 使用唯一的檔名避免平行執行時的衝突
    config_filename = f"temp_ring_{width}_{p_size}_{b_size}_{vcs}_{rate}.txt"
    with open(config_filename, 'w') as f:
        f.write(config_str)

    try:
        # check=False 允許模擬器因為 Deadlock 而 non-zero exit
        result = subprocess.run([BOOKSIM_EXEC, config_filename], capture_output=True, text=True, check=False)
        latency, is_deadlock = parse_booksim_output(result.stdout)

        # 如果沒有印出 latency 且不是明確的 deadlock，可能就是完全飽和/不穩定
        if latency == float('inf') and not is_deadlock:
            # 檢查是否有 error 訊息
            if "Error" in result.stderr or "Error" in result.stdout:
                 is_deadlock = True # 將其歸類為失敗/死結

    except Exception as e:
        latency = float('inf')
        is_deadlock = True

    finally:
        if os.path.exists(config_filename):
            os.remove(config_filename)

    # 回傳這組設定的結果
    return {
        "width": width,
        "packet_size": p_size,
        "buffer_size": b_size,
        "num_vcs": vcs,
        "injection_rate": rate,
        "latency": latency,
        "is_deadlock": is_deadlock
    }

def main():
    print("啟動 Ring DSE BookSim 實際模擬掃描...")

    if not os.path.exists(BOOKSIM_EXEC):
        print(f"錯誤：找不到 BookSim 執行檔 {BOOKSIM_EXEC}")
        return

    # 優化後的代表性參數空間 (共 3 * 2 * 2 * 2 * 2 = 48 種組合)
    widths = [4, 8, 16]
    packet_sizes = [1, 4]
    buffer_sizes = [4, 8]
    num_vcs = [1, 2]
    injection_rates = [0.05, 0.2]

    tasks = []
    for w in widths:
        for p in packet_sizes:
            for b in buffer_sizes:
                for v in num_vcs:
                    for r in injection_rates:
                        tasks.append((w, p, b, v, r))

    print(f"總共產生 {len(tasks)} 個模擬任務。開始平行執行...")

    # 使用 Multiprocessing 加速執行
    num_cores = max(1, multiprocessing.cpu_count() - 1)
    results = []

    with multiprocessing.Pool(processes=num_cores) as pool:
        for i, res in enumerate(pool.imap_unordered(run_simulation, tasks)):
            results.append(res)
            if (i + 1) % 50 == 0:
                print(f"已完成 {i + 1} / {len(tasks)} 個任務...")

    # 將結果整理成結構化字典以便匯出
    structured_results = {}
    for r in results:
        key = f"Ring_{r['width']}"
        if key not in structured_results:
            structured_results[key] = []
        structured_results[key].append({
            "packet_size": r["packet_size"],
            "buffer_size": r["buffer_size"],
            "num_vcs": r["num_vcs"],
            "injection_rate": r["injection_rate"],
            "latency": r["latency"],
            "is_deadlock": r["is_deadlock"]
        })

    with open('report/report_booksim_ring.json', 'w', encoding='utf-8') as f:
        json.dump(structured_results, f, ensure_ascii=False, indent=4)

    print("模擬掃描完成，已匯出至 report/report_booksim_ring.json")

if __name__ == "__main__":
    main()
