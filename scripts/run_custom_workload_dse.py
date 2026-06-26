import sys
import os
import yaml
import json
import subprocess
import re
import tempfile

# Add project root to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dse_tools.converters.booksim_converter import BookSimConverter
from noc_python_model.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
from noc_python_model.metrics import analyze_channel_load
from dse_tools.runners.run_c_model_dse import generate_trace

def run_booksim(config_filepath, booksim_executable):
    try:
        result = subprocess.run([booksim_executable, config_filepath], capture_output=True, text=True, timeout=60)
        output = result.stdout
        latency = float('inf')
        throughput = 0.0

        for line in output.split('\n'):
            if "Packet latency average" in line and "=" in line:
                match = re.search(r"=\s*([0-9.]+)", line)
                if match:
                    latency = float(match.group(1))
            if "Accepted flit rate" in line and "=" in line:
                match = re.search(r"=\s*([0-9.]+)", line)
                if match:
                    throughput = float(match.group(1))

        return latency, throughput
    except Exception as e:
        print(f"BookSim Error: {e}")
        return float('inf'), 0.0

def run_c_model(config_filepath, trace_filepath, c_model_executable):
    try:
        result = subprocess.run([c_model_executable, config_filepath, trace_filepath], capture_output=True, text=True, timeout=60)
        output = result.stdout
        latency = float('inf')
        throughput = 0.0

        for line in output.split('\n'):
            if "Average Latency:" in line:
                match = re.search(r"Average Latency:\s*([0-9.]+)", line)
                if match:
                    latency = float(match.group(1))
            if "Total Throughput:" in line:
                match = re.search(r"Total Throughput:\s*([0-9.]+)", line)
                if match:
                    throughput = float(match.group(1))

        return latency, throughput
    except Exception as e:
        print(f"C Model Error: {e}")
        return float('inf'), 0.0

def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'custom_workload.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        master_config = yaml.safe_load(f)

    topologies = ['mesh', 'torus', 'ring']
    results = {}

    booksim_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'third_party', 'booksim', 'src', 'booksim'))
    c_model_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'noc_c_model', 'noc_sim'))

    if not os.path.exists(booksim_exe):
        print(f"Error: BookSim executable not found at {booksim_exe}")
        return
    if not os.path.exists(c_model_exe):
        print(f"Error: C Model executable not found at {c_model_exe}")
        return

    width = master_config['architecture']['width']
    height = master_config['architecture']['height']
    num_nodes = width * height

    print("Running Custom Workload DSE Across Topologies...")

    for topo in topologies:
        print(f"\nEvaluating Topology: {topo.upper()}")

        # 1. Update master config for current topology
        current_config = yaml.safe_load(yaml.dump(master_config)) # deep copy
        current_config['architecture']['topology'] = topo

        # Adjust dimensions for ring (1D)
        w, h = width, height
        if topo == 'ring':
            w = num_nodes
            h = 1
            current_config['architecture']['width'] = w
            current_config['architecture']['height'] = h

        # 2. Python Theoretical Model (Edge Loads & Hotspots)
        if topo == 'mesh': G = generate_mesh_topology(w, h)
        elif topo == 'torus': G = generate_torus_topology(w, h)
        elif topo == 'ring': G = generate_ring_topology(num_nodes)

        # Modify Python metrics logic to respect array injection rate in theory!
        # Since analyze_channel_load normally doesn't take the array directly,
        # we will fetch the raw edge loads, then apply the array weight ourselves.
        # But wait, analyze_channel_load applies the probability from get_traffic_destinations.
        # We need to scale the final output by the node's injection rate.

        # Let's write a simple wrapper to calculate exact edge loads
        edge_loads_abs = {edge: 0.0 for edge in G.edges()}
        inj_rates = current_config['simulation']['injection_rate']
        matrix_file = os.path.join(os.path.dirname(__file__), '..', current_config['simulation']['custom_matrix_file'])

        import csv
        matrix = []
        with open(matrix_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                matrix.append([float(x) for x in row])

        # Simple XY/DimOrder routing load estimation
        for src in range(num_nodes):
            rate = inj_rates[src] if isinstance(inj_rates, list) else inj_rates
            if rate == 0: continue

            # Normalize probabilities for this source row (excluding self)
            row_sum = sum(p for d, p in enumerate(matrix[src]) if d != src)

            for dst in range(num_nodes):
                prob = matrix[src][dst]
                if prob == 0 or src == dst or row_sum == 0: continue

                norm_prob = prob / row_sum

                # Flow volume = Injection Rate * Normalized Destination Probability
                flow = rate * norm_prob

                # Approximate path (Mesh/Torus X then Y)
                src_x, src_y = src % w, src // w
                dst_x, dst_y = dst % w, dst // w

                curr = src
                curr_x, curr_y = src_x, src_y

                path = []
                while curr_x != dst_x:
                    dist_x = dst_x - curr_x
                    if topo == 'torus' or topo == 'ring':
                        if abs(dist_x) > w / 2.0: step = 1 if dist_x < 0 else -1
                        else: step = 1 if dist_x > 0 else -1
                    else:
                        step = 1 if dist_x > 0 else -1
                    next_x = (curr_x + step) % w
                    next_node = curr_y * w + next_x
                    path.append((curr, next_node))
                    curr_x = next_x
                    curr = next_node

                while curr_y != dst_y:
                    dist_y = dst_y - curr_y
                    if topo == 'torus':
                        if abs(dist_y) > h / 2.0: step = 1 if dist_y < 0 else -1
                        else: step = 1 if dist_y > 0 else -1
                    else:
                        step = 1 if dist_y > 0 else -1
                    next_y = (curr_y + step) % h
                    next_node = next_y * w + curr_x
                    path.append((curr, next_node))
                    curr_y = next_y
                    curr = next_node

                for u, v in path:
                    if (u,v) in edge_loads_abs: edge_loads_abs[(u,v)] += flow
                    elif (v,u) in edge_loads_abs: edge_loads_abs[(v,u)] += flow

        max_load = max(edge_loads_abs.values()) if edge_loads_abs else 0
        serializable_edge_loads = {f"{u}->{v}": round(load, 4) for (u, v), load in edge_loads_abs.items()}

        # 3. BookSim Simulation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".cfg") as tmp_bs_cfg:
            bs_cfg_path = tmp_bs_cfg.name

        converter = BookSimConverter(current_config)
        converter.convert(bs_cfg_path)
        bs_lat, bs_thr = run_booksim(bs_cfg_path, booksim_exe)
        os.remove(bs_cfg_path)

        # 4. C Model Simulation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as tmp_c_cfg:
            yaml.dump(current_config, tmp_c_cfg)
            c_cfg_path = tmp_c_cfg.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".trace") as tmp_trace:
            trace_path = tmp_trace.name

        generate_trace(num_nodes, inj_rates, current_config['simulation']['sim_cycles'], trace_path, 'custom_matrix', w, h, matrix_file)

        c_lat, c_thr = run_c_model(c_cfg_path, trace_path, c_model_exe)

        os.remove(c_cfg_path)
        os.remove(trace_path)

        # 5. Compile Results
        results[topo] = {
            'theory_max_load': max_load,
            'theory_edge_loads': serializable_edge_loads,
            'booksim_latency': bs_lat,
            'booksim_throughput': bs_thr,
            'c_model_latency': c_lat,
            'c_model_throughput': c_thr
        }

        print(f"  Theory Max Channel Load: {max_load:.4f} FLITs/cycle")
        print(f"  BookSim -> Latency: {bs_lat:.2f}, Throughput: {bs_thr:.4f}")
        print(f"  C Model -> Latency: {c_lat:.2f}, Throughput: {c_thr:.4f}")

    output_file = os.path.join(os.path.dirname(__file__), '..', 'reports', 'custom_workload_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
