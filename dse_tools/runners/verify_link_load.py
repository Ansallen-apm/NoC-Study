import sys
import os
import subprocess
import yaml
import re
import tempfile
import numpy as np

# Adjust python path if needed to find noc_python_model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from noc_python_model.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
import networkx as nx

def analyze_channel_load_directed(G, routing_algorithm='xy', traffic_pattern='uniform', width=None, height=None):
    from noc_python_model.metrics import get_traffic_destinations
    num_nodes = G.number_of_nodes()
    edge_loads = {edge: 0.0 for edge in G.edges()}

    for src in G.nodes():
        dests = get_traffic_destinations(src, num_nodes, traffic_pattern, width, height)
        for dst, prob in dests:
            if src != dst:
                topo_type = G.graph.get('type')

                if routing_algorithm == 'xy' and topo_type == 'ring':
                    path = []
                    curr = src
                    while curr != dst:
                        dist = dst - curr
                        if abs(dist) > num_nodes / 2.0:
                            step = 1 if dist < 0 else -1
                        else:
                            step = 1 if dist > 0 else -1
                        next_node = (curr + step) % num_nodes
                        path.append((curr, next_node))
                        curr = next_node

                    for u, v in path:
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += prob

                elif routing_algorithm == 'xy' and topo_type in ['mesh', 'torus']:
                    path = []
                    curr = src
                    src_x, src_y = src % width, src // width
                    dst_x, dst_y = dst % width, dst // width
                    curr_x, curr_y = src_x, src_y

                    # 先走 X 方向
                    while curr_x != dst_x:
                        dist_x = dst_x - curr_x
                        if topo_type == 'torus':
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

                    for u, v in path:
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += prob
                else:
                    path = nx.shortest_path(G, source=src, target=dst)
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        if (u, v) in edge_loads:
                            edge_loads[(u, v)] += prob

    return {f"{u}->{v}": round(load, 4) for (u, v), load in edge_loads.items()}

def run_noc_sim(config_path, trace_path, executable):
    result = subprocess.run([executable, config_path, trace_path], capture_output=True, text=True)

    edge_utils = {}
    total_throughput = 0.0

    lines = result.stdout.splitlines()
    for line in lines:
        if "Total Throughput:" in line:
            m = re.search(r"Total Throughput:\s*([0-9.]+)", line)
            if m:
                total_throughput = float(m.group(1))
        if "Utilization:" in line and "Edge" in line:
            m = re.search(r"Edge (\d+)->(\d+) Utilization: ([0-9.]+)", line)
            if m:
                u, v = m.group(1), m.group(2)
                util = float(m.group(3))
                edge_utils[f"{u}->{v}"] = util
    return edge_utils, total_throughput

def verify_link_load(topo_type, size, rate=0.01, sim_cycles=100000):
    from run_c_model_dse import generate_trace # Reuse the trace generator

    print(f"\n--- Verifying {topo_type} {size}x{size if topo_type != 'ring' else 1} ---")

    # 1. Create config
    width = size
    height = size if topo_type != 'ring' else 1
    num_nodes = width * height

    config_dict = {
        "architecture": {
            "topology": topo_type,
            "routing": "xy" if topo_type == "mesh" else "dim_order" if topo_type == "torus" else "shortest_path",
            "width": width,
            "height": height,
            "buffer_size": 4,
            "frequency_mhz": 1000,
            "flit_width_bits": 128,
            "num_vcs": 2,
            "packet_size": 1 # Single flit packets to match Poisson rate mapping cleanly
        },
        "simulation": {
            "max_cycles": sim_cycles
        }
    }

    # 2. Setup tmp files
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_dict, f)
        config_path = f.name

    with tempfile.NamedTemporaryFile('w', suffix='.trace', delete=False) as f:
        trace_path = f.name

    try:
        # 3. Generate Trace (uniform random)
        generate_trace(num_nodes, rate, sim_cycles, trace_path, "uniform", width, height)

        # 4. Run C++ Sim
        exe = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'noc_c_model', 'noc_sim'))
        actual_utils, throughput = run_noc_sim(config_path, trace_path, exe)

        # 5. Calculate Theoretical Load
        if topo_type == 'mesh':
            G = generate_mesh_topology(width, height)
        elif topo_type == 'torus':
            G = generate_torus_topology(width, height)
        elif topo_type == 'ring':
            G = generate_ring_topology(num_nodes)

        # Convert G to directed graph so each edge is tracked independently
        G_dir = nx.to_directed(G)
        G_dir.graph = G.graph # preserve graph attributes

        routing_algo = config_dict['architecture']['routing']
        if routing_algo == 'dim_order': routing_algo = 'xy'
        if routing_algo == 'shortest_path': routing_algo = 'xy' # Python uses xy for ring logic internally

        theory_loads = analyze_channel_load_directed(G_dir, routing_algo, 'uniform', width, height)

        # Multiply theoretical expectation (load per node injection) by the global actual injection rate per node.
        # Actual per-node injection rate = throughput / num_nodes.
        actual_node_rate = throughput / num_nodes

        # Multiply load expectation by the node injection rate to get theoretical utilization
        expected_utils = {edge: theory_loads.get(edge, 0.0) * actual_node_rate for edge in actual_utils.keys()}

        # 6. Compare
        max_err = 0.0
        print(f"{'Edge':<10} | {'Theory Util':<15} | {'Actual Util':<15} | {'Error':<15}")
        for edge in actual_utils:
            t_u = expected_utils.get(edge, 0.0)
            a_u = actual_utils[edge]
            err = abs(t_u - a_u)
            max_err = max(max_err, err)
            print(f"{edge:<10} | {t_u:<15.6f} | {a_u:<15.6f} | {err:<15.6f}")

        print(f"Max Absolute Error: {max_err:.6f}")
        assert max_err < 0.035, f"Error too large! Max error: {max_err}"

    finally:
        os.remove(config_path)
        os.remove(trace_path)

if __name__ == "__main__":
    verify_link_load("mesh", 4)
    verify_link_load("torus", 4)
    verify_link_load("ring", 8)
