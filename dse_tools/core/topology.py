import networkx as nx

def generate_mesh_topology(width, height):
    G = nx.grid_2d_graph(width, height)
    # Convert node labels from (x, y) tuples to integer IDs
    mapping = {node: node[1] * width + node[0] for node in G.nodes()}
    G = nx.relabel_nodes(G, mapping)
    G.graph['type'] = 'mesh'
    G.graph['width'] = width
    G.graph['height'] = height
    return G

def generate_torus_topology(width, height):
    G = nx.grid_2d_graph(width, height, periodic=True)
    mapping = {node: node[1] * width + node[0] for node in G.nodes()}
    G = nx.relabel_nodes(G, mapping)
    G.graph['type'] = 'torus'
    G.graph['width'] = width
    G.graph['height'] = height
    return G

def generate_ring_topology(num_nodes):
    G = nx.cycle_graph(num_nodes)
    G.graph['type'] = 'ring'
    G.graph['width'] = num_nodes
    G.graph['height'] = 1
    return G
