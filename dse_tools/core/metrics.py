import networkx as nx

def calculate_channel_count(G):
    return G.number_of_edges()

def calculate_average_hop_count(G):
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
    topo_type = G.graph.get('type', 'unknown')
    if topo_type == 'mesh':
        width = G.graph.get('width')
        height = G.graph.get('height')
        return 2 * min(width, height) * channel_bandwidth_bits
    elif topo_type == 'torus':
        width = G.graph.get('width')
        height = G.graph.get('height')
        return 4 * min(width, height) * channel_bandwidth_bits
    elif topo_type == 'ring':
        return 4 * channel_bandwidth_bits
    return 0

def analyze_channel_load(G, routing_algorithm='xy'):
    edge_loads = {edge: 0 for edge in G.edges()}
    width = G.graph.get('width', 0)

    for src in G.nodes():
        for dst in G.nodes():
            if src != dst:
                if routing_algorithm == 'xy' and G.graph.get('type') in ['mesh', 'torus']:
                    path = []
                    curr = src
                    src_x, src_y = src % width, src // width
                    dst_x, dst_y = dst % width, dst // width
                    curr_x, curr_y = src_x, src_y

                    topo_type = G.graph.get('type')
                    height = G.graph.get('height', 1)

                    while curr_x != dst_x:
                        dist_x = dst_x - curr_x
                        if topo_type == 'torus' or topo_type == 'ring':
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

                    for u, v in path:
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += 1
                        elif (v, u) in edge_loads:
                            edge_loads[(v, u)] += 1
                else:
                    path = nx.shortest_path(G, source=src, target=dst)
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += 1
                        elif (v, u) in edge_loads:
                            edge_loads[(v, u)] += 1

    if not edge_loads:
        return {'max_load': 0, 'hot_spots': [], 'all_edge_loads': {}}

    max_load = max(edge_loads.values())
    hot_spots = [edge for edge, load in edge_loads.items() if load == max_load]
    serializable_edge_loads = {f"{u}->{v}": load for (u, v), load in edge_loads.items()}

    return {
        'max_load': max_load,
        'hot_spots': hot_spots,
        'all_edge_loads': serializable_edge_loads
    }
