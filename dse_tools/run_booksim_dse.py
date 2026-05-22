import yaml
import os
import subprocess
import re
import matplotlib.pyplot as plt
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

def main():
    print("啟動 NoC DSE 階段 3：BookSim 交叉驗證掃描...")

    # 讀取主設定檔
    config_path = "NoC_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        master_config = yaml.safe_load(f)

    # 準備注入率掃描範圍 (0.05 到 0.50，間隔 0.05)
    injection_rates = [round(0.05 * i, 2) for i in range(1, 11)]
    latencies = []

    booksim_executable = "../third_party/booksim/src/booksim"
    if not os.path.exists(booksim_executable):
        print(f"錯誤：找不到 BookSim 執行檔於 {booksim_executable}，請先執行 make。")
        return

    # 針對每一個注入率執行掃描
    for rate in injection_rates:
        print(f"測試注入率 (Injection Rate): {rate}")

        # 覆寫主設定檔中的注入率
        master_config['simulation']['injection_rate'] = rate

        # 產生對應的 BookSim 設定檔
        temp_config_path = "temp_booksim_config.txt"
        converter = BookSimConverter(master_config)
        converter.convert(temp_config_path)

        # 執行 BookSim
        try:
            # Note: check=False is used because BookSim might exit with a non-zero code
            # when the network is unstable/saturated, but still print useful latency stats
            # up to the point of failure. We attempt to parse whatever output is given.
            result = subprocess.run([booksim_executable, temp_config_path], capture_output=True, text=True, check=False)
            latency = parse_booksim_output(result.stdout)

            if latency is not None:
                latencies.append(latency)
                print(f"  -> 平均延遲 (Average Latency): {latency} cycles")
            else:
                print("  -> 無法解析延遲 (網路可能已飽和/不穩定)")
                latencies.append(float('inf'))

        except Exception as e:
            print(f"  -> 執行失敗: {e}")
            latencies.append(float('inf'))

    # 清理暫存檔
    if os.path.exists(temp_config_path):
        os.remove(temp_config_path)

    # 繪製圖表
    print("\n繪製延遲與負載圖表 (Latency vs. Injected Load)...")
    plt.figure(figsize=(10, 6))

    # 過濾出有效的點來畫圖 (去除飽和點)
    valid_rates = [r for r, l in zip(injection_rates, latencies) if l != float('inf')]
    valid_latencies = [l for l in latencies if l != float('inf')]

    plt.plot(valid_rates, valid_latencies, marker='o', linestyle='-', color='b', label='BookSim (4x4 Mesh, XY)')

    plt.title('NoC DSE: Latency vs Injected Load')
    plt.xlabel('Injection Rate (flits/node/cycle)')
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    plt.legend()

    plot_filename = "report/booksim_latency_vs_load.png"
    plt.savefig(plot_filename)
    print(f"圖表已儲存至 {plot_filename}")

if __name__ == "__main__":
    main()
