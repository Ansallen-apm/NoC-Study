import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import yaml
from core.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
from core.metrics import calculate_average_hop_count, calculate_bisection_bandwidth, analyze_channel_load

def analyze_topology(name, graph, channel_bandwidth, traffic_pattern='uniform'):
    """
    對單一拓撲圖形進行完整的指標分析。
    """
    print(f"正在分析 {name} ({graph.graph['width']}x{graph.graph['height']}) 拓撲，流量模式: {traffic_pattern}...")

    # 計算各項指標
    avg_hops = calculate_average_hop_count(graph, traffic_pattern=traffic_pattern)
    bisection_bw = calculate_bisection_bandwidth(graph, channel_bandwidth)
    load_analysis = analyze_channel_load(graph, routing_algorithm='xy', traffic_pattern=traffic_pattern)

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
    主程式：解析 NoC_config.yaml，動態產生對應的拓撲、計算指標，並將結果輸出。
    """
    print("啟動 NoC DSE 階段 1：理論指標分析...")

    config_path = "config/NoC_config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到設定檔 {config_path}")
        return

    arch = config.get('architecture', {})
    sim = config.get('simulation', {})

    topo_type = arch.get('topology', 'mesh').lower()
    width = arch.get('width', 4)
    height = arch.get('height', 4)
    traffic_pattern = sim.get('traffic_pattern', 'uniform').lower()

    # Channel bandwidth typically is packet_size or flit width, here using fixed 32 for demo or scaling by packet
    channel_bandwidth = 32

    results = {}

    print(f"從 {config_path} 讀取到拓撲設定: {topo_type} (W:{width}, H:{height}), 流量模式: {traffic_pattern}")

    # 動態產生對應的拓撲
    name = f"{topo_type.capitalize()}_{width}x{height}"

    if topo_type == 'mesh':
        graph = generate_mesh_topology(width, height)
    elif topo_type == 'torus':
        graph = generate_torus_topology(width, height)
    elif topo_type == 'ring':
        graph = generate_ring_topology(width)
        name = f"Ring_{width}"
    else:
        print(f"不支援的拓撲類型: {topo_type}")
        return

    results[name] = analyze_topology(name, graph, channel_bandwidth, traffic_pattern)

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
