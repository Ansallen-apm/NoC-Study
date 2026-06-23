import json
import os
import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports', 'CMN_DSE')
DATA_FILE = os.path.join(REPORTS_DIR, 'data.json')
HTML_FILE = os.path.join(REPORTS_DIR, 'basic_CMN.html')

with open(DATA_FILE, 'r') as f:
    data = json.load(f)

html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>CMN DSE 分析報告</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f7f6; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
        .config-panel {{ background-color: #eef2f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; border-left: 5px solid #3498db; }}
        .config-panel p {{ margin: 5px 0; font-size: 15px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 40px; }}
        th, td {{ border: 1px solid #e0e0e0; padding: 12px; text-align: center; }}
        th {{ background-color: #34495e; color: white; font-weight: 500; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .deadlock {{ background-color: #ffeaea !important; color: #c0392b; font-weight: bold; }}
        .success {{ color: #27ae60; font-weight: bold; }}
        .note {{ font-size: 0.9em; color: #7f8c8d; margin-top: -10px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>片上網路架構探索 (CMN DSE) 分析報告</h1>
        <p class="note">產生時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="config-panel">
            <h3>⚙️ 模擬參數設定</h3>
            <p><strong>拓撲結構 (Topology):</strong> Ring (16 Node) / Mesh (4x4) / Torus (4x4)</p>
            <p><strong>虛擬通道數量 (VC):</strong> 1 (單一實體通道)</p>
            <p><strong>緩衝區大小 (Buffer Size):</strong> 4 flits</p>
            <p><strong>封包大小 (Packet Size):</strong> 1 flit (64 Bytes)</p>
            <p><strong>流量模式 (Traffic Pattern):</strong> Uniform Random (滿載 Injection Rate = 1.0)</p>
        </div>
"""

for freq in [2.5, 1.5]:
    html_content += f"""
        <h2>時脈頻率: {freq} GHz</h2>
        <table>
            <thead>
                <tr>
                    <th rowspan="2">拓撲 (Topology)</th>
                    <th colspan="2">Python 理論模型</th>
                    <th colspan="3">C Model</th>
                    <th colspan="3">BookSim</th>
                </tr>
                <tr>
                    <th>對分頻寬 (GB/s)</th>
                    <th>平均跳數 (Hops)</th>
                    <th>吞吐量 (GB/s)</th>
                    <th>平均延遲 (Cycles)</th>
                    <th>狀態</th>
                    <th>吞吐量 (GB/s)</th>
                    <th>平均延遲 (Cycles)</th>
                    <th>狀態</th>
                </tr>
            </thead>
            <tbody>
    """

    for item in data:
        if item['frequency_GHz'] != freq:
            continue

        topo_name = item['topology'].capitalize()
        py = item['python']
        c_mod = item['c_model']
        bs = item['booksim']

        c_status = "<span class='deadlock'>Deadlock</span>" if c_mod['deadlock'] else "<span class='success'>Success</span>"
        bs_status = "<span class='deadlock'>Deadlock</span>" if bs['deadlock'] else "<span class='success'>Success</span>"

        # 處理 C model 數據
        c_bw = f"{c_mod['bw_GBps']:.2f}" if not c_mod['deadlock'] else "N/A"
        c_lat = f"{c_mod['latency']:.2f}" if not c_mod['deadlock'] else "N/A"

        # 處理 BookSim 數據
        bs_bw = f"{bs['bw_GBps']:.2f}" if not bs['deadlock'] else "N/A"
        bs_lat = f"{bs['latency']:.2f}" if not bs['deadlock'] else "N/A"

        # Deadlock row style if both fail? Just highlight status

        html_content += f"""
                <tr>
                    <td><strong>{topo_name}</strong></td>
                    <td>{py['bisection_bw_GBps']:.2f}</td>
                    <td>{py['avg_hops']:.2f}</td>

                    <td>{c_bw}</td>
                    <td>{c_lat}</td>
                    <td>{c_status}</td>

                    <td>{bs_bw}</td>
                    <td>{bs_lat}</td>
                    <td>{bs_status}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    """

html_content += """
        <div class="note" style="margin-top: 30px;">
            <h3>📌 觀察與結論</h3>
            <ul>
                <li><strong>Deadlock 現象:</strong> 在 VC=1 且使用最短路徑 (Dimension-order) 路由時，Ring 與 Torus 拓撲在 BookSim 中會產生死鎖 (Deadlock)，因為其環狀結構導致循環依賴。這符合 NoC 的基本理論。</li>
                <li><strong>理論 vs. 模擬:</strong> Python 提供的「對分頻寬 (Bisection Bandwidth)」為網路在最理想狀態下橫跨兩半部的理論上限。而 C Model 與 BookSim 的「吞吐量」則是實際在 Uniform Random 滿載流量下量測出的有效頻寬，受限於路由、壅塞與 Buffer 大小，通常遠低於理論上限。</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"HTML report successfully generated at: {HTML_FILE}")
