import sys
import os
import yaml
import subprocess
import re
import multiprocessing
from multiprocessing import Pool
import copy
import tempfile
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

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as temp_file:
        temp_config_path = temp_file.name

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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'NoC_config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        master_config = yaml.safe_load(f)

    # 從 YAML 讀取 sweep range
    sweep_range = master_config.get('simulation', {}).get('sweep_range', {'start': 0.05, 'end': 0.50, 'step': 0.05})

    # 計算浮點數避免誤差
    start = int(sweep_range.get('start', 0.05) * 1000)
    end = int(sweep_range.get('end', 0.50) * 1000)
    step = int(sweep_range.get('step', 0.05) * 1000)

    injection_rates = [float(i) / 1000.0 for i in range(start, end + step, step)]

    booksim_executable = os.path.join(os.path.dirname(__file__), '..', '..', 'third_party', 'booksim', 'src', 'booksim')
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

if __name__ == "__main__":
    # For safe multiprocessing in scripts
    multiprocessing.freeze_support()
    main()
