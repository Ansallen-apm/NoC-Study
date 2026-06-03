import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import networkx as nx

def calculate_channel_count(G):
    """
    計算網路中的實體連線數量 (即圖形的無向邊總數)。

    參數:
        G (nx.Graph): 代表網路拓撲的 NetworkX 圖形物件。

    回傳:
        int: 實體連線數 (Channels)。
    """
    return G.number_of_edges()

import math

def get_traffic_destinations(src, num_nodes, traffic_pattern='uniform', width=None, height=None):
    """
    根據流量模式取得目的節點列表與機率分佈。
    回傳格式: [(dest_node, probability), ...]
    """
    if traffic_pattern == 'uniform':
        # 均勻發送給所有其他節點
        prob = 1.0 / (num_nodes - 1) if num_nodes > 1 else 0
        return [(dst, prob) for dst in range(num_nodes) if dst != src]

    elif traffic_pattern == 'bitcomp':
        # Bit-complement: dest = ~src
        bits = max(1, math.ceil(math.log2(num_nodes)))
        mask = (1 << bits) - 1
        dest = (~src) & mask
        if dest >= num_nodes:
            dest = dest % num_nodes # Fallback if out of bounds, though Booksim typically expects pow2 nodes
        return [(dest, 1.0)] if dest != src else []

    elif traffic_pattern == 'transpose':
        # Transpose: dest_x = src_y, dest_y = src_x
        if width is None or height is None:
            # Fallback to uniform if dimensions aren't provided
            prob = 1.0 / (num_nodes - 1) if num_nodes > 1 else 0
            return [(dst, prob) for dst in range(num_nodes) if dst != src]
        src_x = src % width
        src_y = src // width
        # Assuming square or swapping dimensions; for pure transpose we swap x and y.
        # Note: if height != width, standard transpose might map out of bounds.
        # Booksim typically uses transpose on square meshes.
        dest_x = src_y % width
        dest_y = src_x % height
        dest = dest_y * width + dest_x
        return [(dest, 1.0)] if dest != src else []

    elif traffic_pattern == 'tornado':
        # Tornado: dest_x = (src_x + (k/2 - 1)) % k, dest_y = src_y
        if width is None:
            prob = 1.0 / (num_nodes - 1) if num_nodes > 1 else 0
            return [(dst, prob) for dst in range(num_nodes) if dst != src]
        src_x = src % width
        src_y = src // width
        dest_x = (src_x + (width // 2 - 1)) % width
        dest = src_y * width + dest_x
        return [(dest, 1.0)] if dest != src else []

    # 預設回退到 uniform
    prob = 1.0 / (num_nodes - 1) if num_nodes > 1 else 0
    return [(dst, prob) for dst in range(num_nodes) if dst != src]


def calculate_average_hop_count(G, traffic_pattern='uniform'):
    """
    計算在特定流量模式下，整個網路的預期平均跳數 (Expected Average Hop Count)。

    參數:
        G (nx.Graph): 代表網路拓撲的 NetworkX 圖形物件。
        traffic_pattern (str): 流量模式。

    回傳:
        float: 理論上的平均跳數期望值。
    """
    path_lengths = dict(nx.shortest_path_length(G))

    expected_hops = 0.0
    num_nodes = G.number_of_nodes()
    width = G.graph.get('width')
    height = G.graph.get('height')

    for source in G.nodes():
        dests = get_traffic_destinations(source, num_nodes, traffic_pattern, width, height)
        for dest, prob in dests:
            if source != dest:
                # 節點送出封包的期望跳數 = 最短距離 * 該目的地被選擇的機率
                expected_hops += path_lengths[source][dest] * prob

    # 因為每個節點都會平均地送出封包，我們將總期望值除以節點數，得到整網的平均跳數期望值
    if num_nodes == 0:
        return 0.0

    return expected_hops / num_nodes

def calculate_bisection_bandwidth(G, channel_bandwidth_bits=32):
    """
    計算圖形的理論二分頻寬 (Bisection Bandwidth)。
    此函式嘗試找到圖形的最小邊割集 (Minimum Edge Cut) 來將圖形分為兩等份 (或接近兩等份)。
    由於完美的平均二分圖分割是 NP-Hard 問題，這裡我們針對規則的 Mesh/Torus 使用簡化的理論公式推導。

    參數:
        G (nx.Graph): 代表網路拓撲的 NetworkX 圖形物件。
        channel_bandwidth_bits (int): 單一通道的頻寬 (位元/週期)。預設為 32。

    回傳:
        int: 二分頻寬總量 (位元/週期)。
    """
    topo_type = G.graph.get('type', 'unknown')

    if topo_type == 'mesh':
        # 針對 k x k 的 2D Mesh，切過中間的線數是 k。考慮雙向通道，頻寬為 2 * k * channel_bandwidth
        # 這裡取 min(width, height) 來找最短的切面
        width = G.graph.get('width')
        height = G.graph.get('height')
        min_dim = min(width, height)
        return 2 * min_dim * channel_bandwidth_bits

    elif topo_type == 'torus':
        # 針對 Torus，切割時會切斷兩倍於 Mesh 的線數 (因為環面兩邊都有連結)
        width = G.graph.get('width')
        height = G.graph.get('height')
        min_dim = min(width, height)
        return 4 * min_dim * channel_bandwidth_bits

    elif topo_type == 'ring':
        # 雙向 Ring 切割必定切斷兩條雙向連線 (共 4 個單向通道)
        return 4 * channel_bandwidth_bits

    else:
        # 如果是未知的拓撲，使用 networkx 的 nx.minimum_edge_cut 的近似方法
        # (這裡只取任意兩點間的最小割集，並非嚴格的二等分，僅供參考)
        # 實際上 DSE 會針對特定拓撲撰寫精確公式
        return 0

def analyze_channel_load(G, routing_algorithm='xy', traffic_pattern='uniform'):
    """
    分析在特定流量模式下的通道負載 (Channel Load)，
    並找出潛在的熱點 (Hot Spots)。

    參數:
        G (nx.Graph): 網路拓撲圖。
        routing_algorithm (str): 路由演算法，預設為 'xy'。
        traffic_pattern (str): 流量模式。

    回傳:
        dict: 包含 'max_load' (最大負載期望量) 與 'hot_spots' (熱點邊的列表)。
    """
    # 建立一個字典來計算每條邊期望經過的次數
    # 初始化所有邊的計數為 0.0
    edge_loads = {edge: 0.0 for edge in G.edges()}

    width = G.graph.get('width', 0)
    height = G.graph.get('height', 0)
    num_nodes = G.number_of_nodes()

    for src in G.nodes():
        dests = get_traffic_destinations(src, num_nodes, traffic_pattern, width, height)
        for dst, prob in dests:
            if src != dst:
                if routing_algorithm == 'xy' and G.graph.get('type') in ['mesh', 'torus']:
                    # 實作 XY Routing 計算路徑
                    path = []
                    curr = src
                    src_x, src_y = src % width, src // width
                    dst_x, dst_y = dst % width, dst // width
                    curr_x, curr_y = src_x, src_y

                    topo_type = G.graph.get('type')
                    height = G.graph.get('height', 1)

                    # 先走 X 方向
                    while curr_x != dst_x:
                        dist_x = dst_x - curr_x
                        if topo_type == 'torus' or topo_type == 'ring':
                            # 判斷是否跨越邊界比較近
                            if abs(dist_x) > width / 2.0:
                                step = 1 if dist_x < 0 else -1
                            else:
                                step = 1 if dist_x > 0 else -1
                        else:
                            step = 1 if dist_x > 0 else -1

                        next_x = (curr_x + step) % width
                        next_node = curr_y * width + next_x
                        path.append((curr, next_node))
                        curr_x = next_x
                        curr = next_node

                    # 再走 Y 方向
                    while curr_y != dst_y:
                        dist_y = dst_y - curr_y
                        if topo_type == 'torus':
                            if abs(dist_y) > height / 2.0:
                                step = 1 if dist_y < 0 else -1
                            else:
                                step = 1 if dist_y > 0 else -1
                        else:
                            step = 1 if dist_y > 0 else -1

                        next_y = (curr_y + step) % height
                        next_node = next_y * width + curr_x
                        path.append((curr, next_node))
                        curr_y = next_y
                        curr = next_node

                    # 將路徑上的每一條邊計數加上機率值 (期望負載)
                    for u, v in path:
                        # 找到圖形中對應的邊 (無向圖中 u,v 或 v,u)
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += prob
                        elif (v, u) in edge_loads:
                            edge_loads[(v, u)] += prob
                else:
                    # 如果不是 XY 路由，使用 NetworkX 最短路徑近似
                    path = nx.shortest_path(G, source=src, target=dst)
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += prob
                        elif (v, u) in edge_loads:
                            edge_loads[(v, u)] += prob

    # 找出最大負載
    if not edge_loads:
        return {'max_load': 0, 'hot_spots': [], 'all_edge_loads': {}}

    # 為避免浮點數誤差，取到小數第四位進行比較
    max_load = round(max(edge_loads.values()), 4)
    # 找出所有等於最大負載的邊 (熱點)
    hot_spots = [edge for edge, load in edge_loads.items() if round(load, 4) == max_load]

    # 將所有邊的負載轉換為字串 key 方便 JSON 序列化
    serializable_edge_loads = {f"{u}->{v}": round(load, 4) for (u, v), load in edge_loads.items()}

    return {
        'max_load': max_load,
        'hot_spots': hot_spots,
        'all_edge_loads': serializable_edge_loads
    }
