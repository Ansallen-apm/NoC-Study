import json
import os
import sys
import matplotlib.pyplot as plt
import networkx as nx

# 確保可以匯入上一層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def draw_and_save_heatmap(topology, dim, edge_loads, max_load, output_path):
    # 建立圖形
    G = nx.Graph()
    G.graph['type'] = topology

    if topology == 'mesh' or topology == 'torus':
        width = dim
        height = dim
        G.graph['width'] = width
        G.graph['height'] = height
        # 加入節點與邊
        for i in range(width * height):
            G.add_node(i)

        for y in range(height):
            for x in range(width):
                u = y * width + x
                # 右邊的鄰居
                if x < width - 1:
                    v = y * width + (x + 1)
                    G.add_edge(u, v)
                elif topology == 'torus':
                    v = y * width + 0
                    G.add_edge(u, v)

                # 下面的鄰居
                if y < height - 1:
                    v = (y + 1) * width + x
                    G.add_edge(u, v)
                elif topology == 'torus':
                    v = 0 * width + x
                    G.add_edge(u, v)

        # 計算網格位置
        pos = {i: (i % width, height - 1 - (i // width)) for i in range(width * height)}

    elif topology == 'ring':
        G.graph['width'] = dim
        for i in range(dim):
            G.add_node(i)
            G.add_edge(i, (i + 1) % dim)

        pos = nx.circular_layout(G)
    else:
        return # 不支援的拓撲

    # 準備邊的顏色與粗細
    edge_colors = []
    edge_widths = []

    # 處理雙向合併，因為圖是無向的，但 edge_loads 可能是有向的 "u->v" 或是只有單向紀錄
    # 這裡將有向轉為無向累加
    undirected_loads = {}
    for edge_str, load in edge_loads.items():
        parts = edge_str.split("->")
        if len(parts) == 2:
            u, v = int(parts[0]), int(parts[1])
            edge = tuple(sorted((u, v)))
            undirected_loads[edge] = undirected_loads.get(edge, 0) + load

    # 計算無向圖的最大負載
    local_max_load = max(list(undirected_loads.values()) + [1]) # 避免為 0

    for u, v in G.edges():
        edge = tuple(sorted((u, v)))
        load = undirected_loads.get(edge, 0)

        # 正規化顏色與粗細
        normalized_load = load / local_max_load

        # 顏色：從冷色 (淺藍) 到暖色 (深紅)
        color = plt.cm.jet(normalized_load)
        edge_colors.append(color)

        # 粗細：至少 1.0，最大 5.0
        width = 1.0 + 4.0 * normalized_load
        edge_widths.append(width)

    # 繪圖
    plt.figure(figsize=(8, 8))

    # 繪製節點
    nx.draw_networkx_nodes(G, pos, node_color='lightgray', node_size=300, edgecolors='black')

    # 繪製邊 (熱點)
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, alpha=0.8)

    # 標籤
    nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')

    plt.title(f"{topology.capitalize()} {dim}x{dim if topology != 'ring' else ''} Channel Load Heatmap\nMax Edge Load: {local_max_load}")
    plt.axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

def main():
    report_dir = 'report'
    heatmaps_dir = os.path.join(report_dir, 'heatmaps')
    os.makedirs(heatmaps_dir, exist_ok=True)

    json_path = os.path.join(report_dir, 'verification_results.json')
    if not os.path.exists(json_path):
        print(f"Error: Could not find {json_path}")
        return

    with open(json_path, 'r') as f:
        results = json.load(f)

    print(f"Generating heatmaps to {heatmaps_dir}...")
    count = 0
    for r in results:
        topology = r['topology']
        dim = r['dim']
        edge_loads = r.get('theory_edge_loads', {})
        max_load = r.get('theory_max_load', 1)

        if not edge_loads:
            continue

        output_filename = f"{topology}_{dim}.png"
        output_path = os.path.join(heatmaps_dir, output_filename)

        draw_and_save_heatmap(topology, dim, edge_loads, max_load, output_path)
        count += 1

    print(f"Successfully generated {count} heatmaps.")

if __name__ == "__main__":
    main()
