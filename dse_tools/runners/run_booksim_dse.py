import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
import subprocess
import re
import matplotlib.pyplot as plt
from multiprocessing import Pool
import copy
from converters.booksim_converter import BookSimConverter

def parse_booksim_output(output):
    """
    解析 BookSim 的終端機輸出，萃取封包延遲平均值 (Average Packet Latency)。
    """
    latency = None
    for line in output.split('\n'):
        # 尋找類似: Packet latency average = 15.2 (1 samples)
        match = re.search(r'Packet latency average = ([\d\.]+)', line)
        if match:
            latency = float(match.group(1))
    return latency

def run_single_simulation(args):
    rate, master_config, booksim_executable = args

    # 建立獨立的 config copy
    config = copy.deepcopy(master_config)
    config['simulation']['injection_rate'] = rate

    temp_config_path = f"dse_tools/runners/temp_booksim_config_{rate}.txt"
    converter = BookSimConverter(config)
    converter.convert(temp_config_path)

    latency = float('inf')
    try:
        result = subprocess.run([booksim_executable, temp_config_path], capture_output=True, text=True, check=False)
        parsed_lat = parse_booksim_output(result.stdout)

        # Check for saturation/deadlock
        if "DEADLOCK" in result.stdout or "Error" in result.stderr:
            parsed_lat = float('inf')

        if parsed_lat is not None:
            latency = parsed_lat
    except Exception as e:
        latency = float('inf')
    finally:
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)

    return rate, latency

def main():
    print("啟動 NoC DSE 階段 3：BookSim 交叉驗證掃描 (平行化重構版)...")

    # 讀取主設定檔
    config_path = "dse_tools/config/NoC_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        master_config = yaml.safe_load(f)

    # 從 YAML 讀取 sweep range
    sweep_range = master_config.get('simulation', {}).get('sweep_range', {'start': 0.05, 'end': 0.50, 'step': 0.05})

    # 計算浮點數避免誤差
    start = int(sweep_range.get('start', 0.05) * 1000)
    end = int(sweep_range.get('end', 0.50) * 1000)
    step = int(sweep_range.get('step', 0.05) * 1000)

    injection_rates = [float(i) / 1000.0 for i in range(start, end + step, step)]

    booksim_executable = "third_party/booksim/src/booksim"
    if not os.path.exists(booksim_executable):
        print(f"錯誤：找不到 BookSim 執行檔於 {booksim_executable}，請先執行 make。")
        return

    # 平行處理
    print(f"開始平行模擬，共 {len(injection_rates)} 個注入率點...")
    pool_args = [(rate, master_config, booksim_executable) for rate in injection_rates]

    latencies_dict = {}
    with Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(run_single_simulation, pool_args)

    for rate, lat in results:
        latencies_dict[rate] = lat
        if lat != float('inf'):
            print(f"  Rate: {rate:.3f} -> 平均延遲 (Average Latency): {lat} cycles")
        else:
            print(f"  Rate: {rate:.3f} -> 網路飽和/不穩定")

    # 繪製圖表
    print("\n繪製延遲與負載圖表 (Latency vs. Injected Load)...")
    plt.figure(figsize=(10, 6))

    # 確保按照順序畫圖
    sorted_rates = sorted(latencies_dict.keys())
    valid_rates = [r for r in sorted_rates if latencies_dict[r] != float('inf')]
    valid_latencies = [latencies_dict[r] for r in valid_rates]

    topo_name = master_config.get('architecture', {}).get('topology', 'mesh')

    plt.plot(valid_rates, valid_latencies, marker='o', linestyle='-', color='b', label=f'BookSim ({topo_name})')

    plt.title('NoC DSE: Latency vs Injected Load')
    plt.xlabel('Injection Rate (flits/node/cycle)')
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    plt.legend()

    os.makedirs("dse_tools/report", exist_ok=True)
    plot_filename = "dse_tools/report/booksim_latency_vs_load.png"
    plt.savefig(plot_filename)
    print(f"圖表已儲存至 {plot_filename}")

if __name__ == "__main__":
    import multiprocessing
    # For safe multiprocessing in scripts
    multiprocessing.freeze_support()
    main()
