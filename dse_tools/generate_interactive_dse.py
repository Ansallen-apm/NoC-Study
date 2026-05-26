import json

def generate_interactive_html():
    with open('report/verification_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)

    # 準備給 Chart.js 的資料集
    chart_data = {
        "mesh": [],
        "torus": [],
        "ring": []
    }

    for r in results:
        topo = r['topology']
        dim = r['dim']
        nodes = r['nodes']
        label = f"{topo.capitalize()} (Dim: {dim}, Nodes: {nodes})"

        curve = r.get('latency_curve', [])

        # 過濾 inf，並將資料轉為 {x: rate, y: latency} 格式
        data_points = []
        for point in curve:
            if point['latency'] != float('inf'):
                data_points.append({"x": point['rate'], "y": point['latency']})

        if data_points:
            chart_data[topo].append({
                "label": label,
                "data": data_points
            })

    # 將 Python dict 轉為 JSON string 嵌入 HTML
    chart_data_json = json.dumps(chart_data)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>互動式 DSE 效能趨勢報告</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ color: #2c3e50; text-align: center; }}
            .controls {{ text-align: center; margin: 20px 0; }}
            select {{ padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #ccc; }}
            .chart-container {{ position: relative; height: 60vh; width: 100%; }}
        </style>
    </head>
    <body>

    <div class="container">
        <h1>互動式 NoC DSE 效能趨勢 (Latency vs. Load)</h1>

        <div class="controls">
            <label for="topoSelect"><strong>選擇拓撲 (Select Topology): </strong></label>
            <select id="topoSelect" onchange="updateChart()">
                <option value="mesh">Mesh (網格)</option>
                <option value="torus">Torus (環面網格)</option>
                <option value="ring">Ring (環狀)</option>
            </select>
        </div>

        <div class="chart-container">
            <canvas id="dseChart"></canvas>
        </div>
    </div>

    <script>
        // 來自 Python 的完整 DSE 曲線資料
        const allData = {chart_data_json};

        // 預設顏色庫
        const colors = [
            '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
            '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'
        ];

        let myChart = null;

        function updateChart() {{
            const selectedTopo = document.getElementById('topoSelect').value;
            const datasets = allData[selectedTopo];

            // 替每個 dataset 上色
            datasets.forEach((ds, index) => {{
                ds.borderColor = colors[index % colors.length];
                ds.backgroundColor = colors[index % colors.length];
                ds.fill = false;
                ds.tension = 0.1;
                ds.pointRadius = 5;
                ds.pointHoverRadius = 8;
            }});

            const ctx = document.getElementById('dseChart').getContext('2d');

            if (myChart) {{
                myChart.destroy();
            }}

            myChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{
                                display: true,
                                text: '注入率 (Injection Rate) [flits/node/cycle]',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            min: 0
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: '平均延遲 (Average Latency) [cycles]',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            min: 0,
                            suggestedMax: 100 // 可避免 Y 軸被單一飆高的點拉得太誇張
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': Rate ' + context.parsed.x + ' -> Latency ' + context.parsed.y + ' cycles';
                                }}
                            }}
                        }},
                        legend: {{
                            position: 'right'
                        }}
                    }}
                }}
            }});
        }}

        // 初始化
        window.onload = updateChart;
    </script>
    </body>
    </html>
    """

    output_path = 'report/interactive_dse_trends.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"互動式 HTML 報告已產生：{output_path}")

if __name__ == "__main__":
    generate_interactive_html()
