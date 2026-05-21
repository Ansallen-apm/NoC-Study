import json
import os

def generate_html(theory_data, booksim_data, output_filepath):
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>NoC DSE: Ring Topology Case Study Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; color: #333; }
            h1, h2, h3 { color: #0056b3; }
            .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            th { background-color: #0056b3; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .deadlock { background-color: #ffcccc !important; color: #cc0000; font-weight: bold; }
            .success { color: #008000; font-weight: bold; }
            .note { font-size: 0.9em; color: #666; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>片上網路架構探索 (NoC DSE)</h1>
            <h2>Ring 拓撲 Case Study 比較報告</h2>
            <p class="note">本報告匯集了 Python 理論推導與 BookSim 實際模擬的交叉驗證結果。</p>

            <h3>1. 理論分析 (Theoretical Analysis)</h3>
            <table>
                <tr>
                    <th>節點數 (Nodes)</th>
                    <th>平均跳數 (Avg Hops)</th>
                    <th>二分頻寬 (Bisection BW)</th>
                    <th>最大理論注入率 (Max Inj Rate)</th>
                </tr>
    """

    # 寫入理論表格
    # 為了排序，我們先對 nodes 進行排序
    sorted_theory = sorted(theory_data.values(), key=lambda x: x['nodes'])
    for t in sorted_theory:
        html_content += f"""
                <tr>
                    <td>{t['nodes']}</td>
                    <td>{t['average_hops']}</td>
                    <td>{t['bisection_bandwidth_bps']} bps</td>
                    <td>{t['theoretical_max_injection_rate']} flits/node/cycle</td>
                </tr>
        """

    html_content += """
            </table>

            <h3>2. BookSim 模擬結果 (BookSim Simulation Results)</h3>
            <p class="note">比較不同配置在注入率 0.2 時的表現。注意：在 1D Torus (Ring) 中，若 VC=1 且使用 shortest path routing，必定發生死結 (Deadlock/Infinity Latency)。</p>
            <table>
                <tr>
                    <th>拓撲 (Topology)</th>
                    <th>封包大小 (Packet Size)</th>
                    <th>緩衝區大小 (Buffer Size)</th>
                    <th>虛擬通道數 (VCs)</th>
                    <th>延遲 (Latency) [Inj Rate=0.2]</th>
                    <th>狀態 (Status)</th>
                </tr>
    """

    # 篩選出特定資料來顯示以避免表格過長
    # 我們只看 injection_rate = 0.2 的資料，並選幾個代表性的 nodes (4, 8, 16)
    target_nodes = [4, 8, 16]

    for node_size in target_nodes:
        key = f"Ring_{node_size}"
        if key in booksim_data:
            # 為了乾淨的展示，我們固定看 Buffer Size = 8 的表現，來比較 VC=1 和 VC=2
            for p_size in [2, 8]:
                for vcs in [1, 2]:
                    # 尋找匹配的設定
                    record = next((r for r in booksim_data[key] if r['injection_rate'] == 0.2 and r['buffer_size'] == 8 and r['packet_size'] == p_size and r['num_vcs'] == vcs), None)

                    if record:
                        lat = record['latency']
                        is_deadlock = record['is_deadlock']

                        if is_deadlock or lat == float('inf'):
                            status_class = "deadlock"
                            status_text = "Deadlock / Saturated"
                            lat_text = "∞"
                        else:
                            status_class = "success"
                            status_text = "Success"
                            lat_text = f"{lat:.2f} cycles"

                        html_content += f"""
                        <tr class="{status_class if is_deadlock or lat == float('inf') else ''}">
                            <td>Ring (Nodes: {node_size})</td>
                            <td>{p_size} flits</td>
                            <td>8 flits</td>
                            <td>{vcs}</td>
                            <td>{lat_text}</td>
                            <td class="{status_class}">{status_text}</td>
                        </tr>
                        """

    html_content += """
            </table>

            <h3>3. 交叉驗證結論 (Cross-Verification Conclusion)</h3>
            <ul>
                <li><strong>理論 vs. 實際：</strong> 理論模型成功計算出 Ring 拓撲隨節點增加而遞減的「最大理論注入率」。這與 BookSim 在高節點數時容易遇到瓶頸的現象一致。</li>
                <li><strong>死結驗證 (Deadlock Verification)：</strong> 在 <code>dim_order</code> (最短路徑) 路由下，BookSim 完美印證了理論：<strong>當 VC=1 時，封包循環等待造成死結</strong>；當 VC=2 時，BookSim 的 dateline 機制成功打破循環，網路能正常運作。</li>
                <li><strong>封包與延遲：</strong> 在相同的注入率與 Buffer 大小下，封包大小 (Packet Size) 越長，Head-of-Line Blocking 越嚴重，導致平均延遲上升。</li>
            </ul>
        </div>
    </body>
    </html>
    """

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    print("產生 HTML 報告...")

    with open('report_theory_ring.json', 'r', encoding='utf-8') as f:
        theory_data = json.load(f)

    with open('report_booksim_ring.json', 'r', encoding='utf-8') as f:
        booksim_data = json.load(f)

    generate_html(theory_data, booksim_data, 'ring_dse_comparison.html')
    print("報告產生完畢：ring_dse_comparison.html")

if __name__ == "__main__":
    main()
