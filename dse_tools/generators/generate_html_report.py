import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.html_gen.lib.html_utils import render_template, save_html

def generate_html(theory_data, booksim_data, output_filepath):
    sorted_theory = sorted(theory_data.values(), key=lambda x: x['nodes'])

    target_nodes = [4, 6, 8, 10, 16]
    target_rate = 0.3

    booksim_rows = []
    for node_size in target_nodes:
        key = f"Ring_{node_size}"
        if key in booksim_data:
            for p_size in [2, 4]:
                for vcs in [1, 2, 4]:
                    record = next((r for r in booksim_data[key] if r['injection_rate'] == target_rate and r['buffer_size'] == 8 and r['packet_size'] == p_size and r['num_vcs'] == vcs), None)
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

                        booksim_rows.append({
                            'node_size': node_size,
                            'p_size': p_size,
                            'vcs': vcs,
                            'status_class': status_class,
                            'status_text': status_text,
                            'lat_text': lat_text
                        })

    # 計算圖表資料: 理論 vs BookSim 最大成功注入率 (VC=2, Packet Size=2)
    chart_labels = []
    theory_chart_data = []
    booksim_chart_data = []

    for node_size in target_nodes:
        chart_labels.append(str(node_size))

        # 理論最大注入率
        t_record = next((t for t in sorted_theory if t['nodes'] == node_size), None)
        if t_record:
            theory_chart_data.append(t_record['theoretical_max_injection_rate'])
        else:
            theory_chart_data.append(0)

        # BookSim 實際最大成功注入率 (VC=2, Packet Size=2)
        key = f"Ring_{node_size}"
        max_succ_rate = 0.0
        if key in booksim_data:
            # 取出符合條件的所有紀錄並依注入率排序
            records = [r for r in booksim_data[key] if r['num_vcs'] == 2 and r['packet_size'] == 2 and r['buffer_size'] == 8]
            records = sorted(records, key=lambda x: x['injection_rate'])

            for r in records:
                if not r['is_deadlock'] and r['latency'] != float('inf'):
                    max_succ_rate = r['injection_rate']
                else:
                    # 遇到失敗就停止，前面的最高成功率即為飽和點
                    break
        booksim_chart_data.append(max_succ_rate)

    html_content = render_template('html_report.html', base_path="../../../",
                                   sorted_theory=sorted_theory,
                                   target_rate=target_rate,
                                   booksim_rows=booksim_rows,
                                   chart_labels=json.dumps(chart_labels),
                                   theory_chart_data=json.dumps(theory_chart_data),
                                   booksim_chart_data=json.dumps(booksim_chart_data),
                                   chart_js=True)

    save_html(html_content, output_filepath)

def main():
    print("產生 HTML 報告...")

    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "report_theory_ring.json"), 'r', encoding='utf-8') as f:
            theory_data = json.load(f)
    except Exception as e:
        print(f"錯誤：讀取 report_theory_ring.json 失敗 ({e})。")
        theory_data = {}

    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "report_full_booksim_ring.json"), 'r', encoding='utf-8') as f:
            booksim_data = json.load(f)
    except Exception as e:
        print(f"錯誤：讀取 report_full_booksim_ring.json 失敗 ({e})。")
        booksim_data = {}

    generate_html(theory_data, booksim_data, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "html", "full_ring_dse_comparison.html"))
    print("報告產生完畢：reports/full_ring_dse_comparison.html")

if __name__ == "__main__":
    main()
