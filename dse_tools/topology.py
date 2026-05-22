import networkx as nx

def generate_mesh_topology(width, height):
    """
    產生 2D Mesh 拓撲結構。

    參數:
        width (int): Mesh 的寬度 (X軸節點數)
        height (int): Mesh 的高度 (Y軸節點數)

    回傳:
        nx.Graph: 代表 Mesh 拓撲的圖形物件。節點名稱為 (x, y) 座標的字串或 tuple。
    """
    # 使用 networkx 內建的 grid_2d_graph 產生 mesh
    # 產生的節點會是 (x, y) 形式的 tuple
    G = nx.grid_2d_graph(width, height)

    # 將節點轉換為整數 ID (從 0 到 width*height - 1)，方便後續與陣列對應
    # 對應規則：id = y * width + x
    mapping = {(x, y): y * width + x for x, y in G.nodes()}
    G_int = nx.relabel_nodes(G, mapping)

    # 儲存額外的拓撲資訊
    G_int.graph['type'] = 'mesh'
    G_int.graph['width'] = width
    G_int.graph['height'] = height
    G_int.graph['num_nodes'] = width * height

    return G_int

def generate_ring_topology(nodes):
    """
    產生 Ring (1D Torus) 拓撲結構。

    參數:
        nodes (int): Ring 的總節點數。

    回傳:
        nx.Graph: 代表 Ring 拓撲的圖形物件。
    """
    G = nx.cycle_graph(nodes)

    # 儲存額外的拓撲資訊
    G.graph['type'] = 'ring'
    G.graph['width'] = nodes
    G.graph['height'] = 1
    G.graph['num_nodes'] = nodes

    return G

def generate_torus_topology(width, height):
    """
    產生 2D Torus 拓撲結構 (邊緣相連的 Mesh)。

    參數:
        width (int): Torus 的寬度
        height (int): Torus 的高度

    回傳:
        nx.Graph: 代表 Torus 拓撲的圖形物件。
    """
    # periodic=True 代表邊緣會自動連接形成環面
    G = nx.grid_2d_graph(width, height, periodic=True)

    # 將節點轉換為整數 ID
    mapping = {(x, y): y * width + x for x, y in G.nodes()}
    G_int = nx.relabel_nodes(G, mapping)

    # 儲存額外的拓撲資訊
    G_int.graph['type'] = 'torus'
    G_int.graph['width'] = width
    G_int.graph['height'] = height
    G_int.graph['num_nodes'] = width * height

    return G_int
