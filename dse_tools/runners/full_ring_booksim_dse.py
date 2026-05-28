import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import subprocess
import multiprocessing
import re

BOOKSIM_EXEC = "../third_party/booksim/src/booksim"
REPORT_FILE = "report/report_full_booksim_ring.json"

def generate_config_string(width, packet_size, buffer_size, num_vcs, injection_rate):
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

    config_filename = f"temp_full_ring_{width}_{p_size}_{b_size}_{vcs}_{rate}.txt"
    with open(config_filename, 'w') as f:
        f.write(config_str)

    try:
        result = subprocess.run([BOOKSIM_EXEC, config_filename], capture_output=True, text=True, check=False)
        latency, is_deadlock = parse_booksim_output(result.stdout)

        if latency == float('inf') and not is_deadlock:
            if "Error" in result.stderr or "Error" in result.stdout:
                 is_deadlock = True

    except Exception as e:
        latency = float('inf')
        is_deadlock = True

    finally:
        if os.path.exists(config_filename):
            os.remove(config_filename)

    return {
        "width": width,
        "routing": "dim_order",
        "traffic": "uniform",
        "packet_size": p_size,
        "buffer_size": b_size,
        "num_vcs": vcs,
        "injection_rate": rate,
        "latency": latency,
        "is_deadlock": is_deadlock
    }

def main():
    print("啟動完整的 Ring DSE BookSim 實際模擬掃描 (支援斷點續傳)...")

    if not os.path.exists(BOOKSIM_EXEC):
        print(f"錯誤：找不到 BookSim 執行檔 {BOOKSIM_EXEC}")
        return

    # 定義完整的參數空間
    widths = [4, 6, 8, 10, 16]
    packet_sizes = [1, 2, 4, 8]
    buffer_sizes = [2, 4, 8, 16]
    num_vcs = [1, 2, 4]
    injection_rates = [0.1, 0.3, 0.5]

    # 讀取 Checkpoint
    existing_results = {}
    completed_task_signatures = set()
    if os.path.exists(REPORT_FILE):
        try:
            with open(REPORT_FILE, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
                for key, runs in existing_results.items():
                    for r in runs:
                        sig = (int(key.split('_')[1]), r['packet_size'], r['buffer_size'], r['num_vcs'], r['injection_rate'])
                        completed_task_signatures.add(sig)
            print(f"已讀取斷點紀錄，發現 {len(completed_task_signatures)} 筆已完成的模擬。")
        except json.JSONDecodeError:
            print("警告：讀取 Checkpoint 失敗，將從頭開始執行。")

    all_tasks = []
    for w in widths:
        for p in packet_sizes:
            for b in buffer_sizes:
                # 限制：Buffer 不能小於 Packet
                if b < p:
                    continue
                for v in num_vcs:
                    for r in injection_rates:
                        all_tasks.append((w, p, b, v, r))

    pending_tasks = [t for t in all_tasks if t not in completed_task_signatures]
    print(f"總組合數: {len(all_tasks)}")
    print(f"待執行任務數: {len(pending_tasks)}")

    if not pending_tasks:
        print("所有任務皆已完成！")
        return

    # 執行未完成的任務
    num_cores = max(1, multiprocessing.cpu_count()) # 開滿硬體資源
    new_results = []

    print(f"開始平行執行，使用 {num_cores} 個核心...")
    with multiprocessing.Pool(processes=num_cores) as pool:
        for i, res in enumerate(pool.imap_unordered(run_simulation, pending_tasks)):
            new_results.append(res)
            if (i + 1) % 50 == 0 or (i + 1) == len(pending_tasks):
                print(f"本次執行進度: {i + 1} / {len(pending_tasks)} 個任務...")

                # 每隔一段時間就儲存一次進度 (Checkpoint)
                structured_results = dict(existing_results) # 複製原本的結果
                for nr in new_results:
                    k = f"Ring_{nr['width']}"
                    if k not in structured_results:
                        structured_results[k] = []
                    # 避免重複寫入
                    existing_sigs = {(er['packet_size'], er['buffer_size'], er['num_vcs'], er['injection_rate']) for er in structured_results[k]}
                    sig = (nr['packet_size'], nr['buffer_size'], nr['num_vcs'], nr['injection_rate'])
                    if sig not in existing_sigs:
                        structured_results[k].append({
                            "routing": nr["routing"],
                            "traffic": nr["traffic"],
                            "packet_size": nr["packet_size"],
                            "buffer_size": nr["buffer_size"],
                            "num_vcs": nr["num_vcs"],
                            "injection_rate": nr["injection_rate"],
                            "latency": nr["latency"],
                            "is_deadlock": nr["is_deadlock"]
                        })

                with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(structured_results, f, ensure_ascii=False, indent=4)

    print(f"模擬掃描全部完成，結果已保存至 {REPORT_FILE}")

if __name__ == "__main__":
    main()
