import json
import yaml
from topology import generate_mesh_topology, generate_torus_topology
from metrics import calculate_average_hop_count, calculate_bisection_bandwidth, analyze_channel_load

def analyze_topology(name, graph, channel_bandwidth):
    """
    對單一拓撲圖形進行完整的指標分析。
    """
    print(f"正在分析 {name} ({graph.graph['width']}x{graph.graph['height']}) 拓撲...")

    # 計算各項指標
    avg_hops = calculate_average_hop_count(graph)
    bisection_bw = calculate_bisection_bandwidth(graph, channel_bandwidth)
    load_analysis = analyze_channel_load(graph, routing_algorithm='xy')

    # 格式化並回傳結果
    return {
        "topology": name,
        "nodes": graph.graph['num_nodes'],
        "metrics": {
            "average_hop_count": round(avg_hops, 4),
            "bisection_bandwidth_bits_per_cycle": bisection_bw,
            "max_channel_load": load_analysis['max_load'],
            "hot_spots_count": len(load_analysis['hot_spots']),
            "hot_spots_edges": [list(edge) for edge in load_analysis['hot_spots']] # 轉為 list 以便 JSON 序列化
        }
    }

def main():
    """
    主程式：負責產生拓撲、計算指標，並將結果輸出為 JSON 與 YAML。
    """
    print("啟動 NoC DSE 階段 1：理論指標分析...")

    channel_bandwidth = 32 # 預設通道頻寬 (位元/週期)
    results = {}

    # 1. 分析 4x4 Mesh
    mesh_4x4 = generate_mesh_topology(4, 4)
    results["Mesh_4x4"] = analyze_topology("Mesh_4x4", mesh_4x4, channel_bandwidth)

    # 2. 分析 4x4 Torus
    torus_4x4 = generate_torus_topology(4, 4)
    results["Torus_4x4"] = analyze_topology("Torus_4x4", torus_4x4, channel_bandwidth)

    # 3. 輸出結果為 JSON 檔案
    json_filename = "report/dse_theory_results.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n分析完成！結果已儲存為 JSON 檔案：{json_filename}")

    # 4. 輸出結果為 YAML 檔案
    yaml_filename = "report/dse_theory_results.yaml"
    with open(yaml_filename, 'w', encoding='utf-8') as f:
        yaml.dump(results, f, allow_unicode=True, default_flow_style=False)
    print(f"分析完成！結果已儲存為 YAML 檔案：{yaml_filename}")

if __name__ == "__main__":
    main()
