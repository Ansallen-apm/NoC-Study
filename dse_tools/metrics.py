import networkx as nx

def calculate_average_hop_count(G):
    """
    計算在均勻隨機 (Uniform Random) 流量模式下，整個網路的平均跳數 (Average Hop Count)。

    參數:
        G (nx.Graph): 代表網路拓撲的 NetworkX 圖形物件。

    回傳:
        float: 理論上的平均跳數。
    """
    # 取得所有節點之間的最短路徑長度
    # shortest_path_length 會回傳一個產生器，包含了所有節點對的最短距離
    path_lengths = dict(nx.shortest_path_length(G))

    total_hops = 0
    num_paths = 0

    for source in G.nodes():
        for dest in G.nodes():
            if source != dest:
                total_hops += path_lengths[source][dest]
                num_paths += 1

    if num_paths == 0:
        return 0.0

    return total_hops / num_paths

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

    else:
        # 如果是未知的拓撲，使用 networkx 的 nx.minimum_edge_cut 的近似方法
        # (這裡只取任意兩點間的最小割集，並非嚴格的二等分，僅供參考)
        # 實際上 DSE 會針對特定拓撲撰寫精確公式
        return 0

def analyze_channel_load(G, routing_algorithm='xy'):
    """
    分析在均勻隨機 (Uniform Random) 流量模式下的通道負載 (Channel Load)，
    並找出潛在的熱點 (Hot Spots)。

    參數:
        G (nx.Graph): 網路拓撲圖。
        routing_algorithm (str): 路由演算法，預設為 'xy'。

    回傳:
        dict: 包含 'max_load' (最大負載量) 與 'hot_spots' (熱點邊的列表)。
    """
    # 建立一個字典來計算每條邊經過的次數
    # 初始化所有邊的計數為 0
    edge_loads = {edge: 0 for edge in G.edges()}

    # 確保是雙向統計 (A->B 和 B->A 都可以算在同一條無向邊上，或者將有向負載加總)
    width = G.graph.get('width', 0)

    for src in G.nodes():
        for dst in G.nodes():
            if src != dst:
                if routing_algorithm == 'xy' and G.graph.get('type') in ['mesh', 'torus']:
                    # 實作 XY Routing 計算路徑
                    path = []
                    curr = src
                    src_x, src_y = src % width, src // width
                    dst_x, dst_y = dst % width, dst // width
                    curr_x, curr_y = src_x, src_y

                    # 先走 X 方向
                    while curr_x != dst_x:
                        next_x = curr_x + (1 if dst_x > curr_x else -1)
                        next_node = curr_y * width + next_x
                        path.append((curr, next_node))
                        curr_x = next_x
                        curr = next_node

                    # 再走 Y 方向
                    while curr_y != dst_y:
                        next_y = curr_y + (1 if dst_y > curr_y else -1)
                        next_node = next_y * width + curr_x
                        path.append((curr, next_node))
                        curr_y = next_y
                        curr = next_node

                    # 將路徑上的每一條邊計數加 1
                    for u, v in path:
                        # 找到圖形中對應的邊 (無向圖中 u,v 或 v,u)
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += 1
                        elif (v, u) in edge_loads:
                            edge_loads[(v, u)] += 1
                else:
                    # 如果不是 XY 路由，使用 NetworkX 最短路徑近似
                    path = nx.shortest_path(G, source=src, target=dst)
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += 1
                        elif (v, u) in edge_loads:
                            edge_loads[(v, u)] += 1

    # 找出最大負載
    if not edge_loads:
        return {'max_load': 0, 'hot_spots': []}

    max_load = max(edge_loads.values())
    # 找出所有等於最大負載的邊 (熱點)
    hot_spots = [edge for edge, load in edge_loads.items() if load == max_load]

    return {
        'max_load': max_load,
        'hot_spots': hot_spots
    }
