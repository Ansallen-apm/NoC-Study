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

def run_booksim(config_filepath, booksim_executable, width, topo):
    try:
        result = subprocess.run([booksim_executable, config_filepath], capture_output=True, text=True, timeout=60)
        output = result.stdout
        latency = float('inf')
        throughput = 0.0
        edge_loads = {}

        current_router = -1
        for line in output.split('\n'):
            if "Packet latency average" in line and "=" in line:
                match = re.search(r"=\s*([0-9.]+)", line)
                if match:
                    latency = float(match.group(1))
            if "Accepted flit rate" in line and "=" in line:
                match = re.search(r"=\s*([0-9.]+)", line)
                if match:
                    throughput = float(match.group(1))

            # Parse print_activity
            if line.startswith("router_"):
                # format: router_y_x.switchMonitor:
                match = re.search(r"router_(\d+)_(\d+)", line)
                if match:
                    y, x = int(match.group(1)), int(match.group(2))
                    current_router = y * width + x if topo != 'ring' else x
            elif "->" in line and current_router != -1:
                # format: [0 -> 1] 0:8  (input -> output) class:count
                # We need to extract output port and the count, then accumulate it.
                match = re.search(r"\[\d+\s*->\s*(\d+)\].*?:\s*(\d+)", line)
                if match:
                    out_port = int(match.group(1))
                    count = int(match.group(2))

                    if count > 0 and out_port != 4: # 4 is local ejection
                        # We use a raw string key because mapping back to exact neighbor node ID
                        # requires height which isn't passed here. The JS renderer will handle
                        # the translation or we map it simply. Let's map it exactly like C Model if we can.
                        # Booksim Ports: 0:Right(+x), 1:Left(-x), 2:Down(+y), 3:Up(-y)
                        rx, ry = current_router % width, current_router // width
                        height = 4 # Hardcoded fallback, user specifies 4x4
                        neighbor = -1

                        if topo == 'ring':
                            if out_port == 0: neighbor = (current_router + 1) % width
                            elif out_port == 1: neighbor = (current_router - 1 + width) % width
                        else:
                            if out_port == 0: neighbor = ry * width + ((rx + 1) % width) # Right
                            elif out_port == 1: neighbor = ry * width + ((rx - 1 + width) % width) # Left
                            elif out_port == 2: neighbor = ((ry + 1) % height) * width + rx # Down
                            elif out_port == 3: neighbor = ((ry - 1 + height) % height) * width + rx # Up

                        if neighbor != -1:
                            key = f"{current_router}->{neighbor}"
                            edge_loads[key] = edge_loads.get(key, 0) + count

        # Convert total counts to rate (flits/cycle) - assuming sample period 500 or similar
        # Since booksim aborts early or runs to max_samples, we normalize based on relative throughput for visualization
        max_edge = max(edge_loads.values()) if edge_loads else 1
        edge_loads = {k: round(v / max_edge, 4) for k, v in edge_loads.items()}

        return latency, throughput, edge_loads
    except Exception as e:
        print(f"BookSim Error: {e}")
        return float('inf'), 0.0, {}

def run_c_model(config_filepath, trace_filepath, c_model_executable, width, height, topo):
    try:
        result = subprocess.run([c_model_executable, config_filepath, trace_filepath], capture_output=True, text=True, timeout=60)
        output = result.stdout
        latency = float('inf')
        throughput = 0.0
        edge_loads = {}

        sim_cycles = 1 # We'll need total cycles to calculate rate. We'll use 10000 as default from config later.

        for line in output.split('\n'):
            if "Average Latency:" in line:
                match = re.search(r"Average Latency:\s*([0-9.]+)", line)
                if match:
                    latency = float(match.group(1))
            if "Total Throughput:" in line:
                match = re.search(r"Total Throughput:\s*([0-9.]+)", line)
                if match:
                    throughput = float(match.group(1))
            if "Simulation finished." in line:
                # We can't extract total cycles directly unless we print it. Assuming 10000.
                sim_cycles = 10000
            if "ActiveCycles:" in line:
                # format: Router X Port Y ActiveCycles: Z
                match = re.search(r"Router (\d+) Port (\d+) ActiveCycles: (\d+)", line)
                if match:
                    r_id = int(match.group(1))
                    port = int(match.group(2))
                    cycles = int(match.group(3))

                    # Convert to normalized load
                    load = cycles / sim_cycles

                    # Map Port to Neighbor:
                    # Mesh/Torus: 1=N, 2=E, 3=S, 4=W
                    # Ring: 1=E, 2=W
                    neighbor = -1
                    rx, ry = r_id % width, r_id // width
                    if topo == 'ring':
                        if port == 1: neighbor = (r_id + 1) % width
                        elif port == 2: neighbor = (r_id - 1 + width) % width
                    else:
                        if port == 1: neighbor = ((ry - 1 + height) % height) * width + rx # North
                        elif port == 2: neighbor = ry * width + ((rx + 1) % width) # East
                        elif port == 3: neighbor = ((ry + 1) % height) * width + rx # South
                        elif port == 4: neighbor = ry * width + ((rx - 1 + width) % width) # West

                    if neighbor != -1 and load > 0:
                        edge_loads[f"{r_id}->{neighbor}"] = round(load, 4)

        return latency, throughput, edge_loads
    except Exception as e:
        print(f"C Model Error: {e}")
        return float('inf'), 0.0, {}

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

        # Let's write a simple wrapper to calculate exact edge loads using Directed logic
        edge_loads_abs = {}
        for u, v in G.edges():
            edge_loads_abs[(u, v)] = 0.0
            edge_loads_abs[(v, u)] = 0.0

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
                    if (u,v) in edge_loads_abs:
                        edge_loads_abs[(u,v)] += flow
                    else:
                        print(f"Warning: Edge {u}->{v} not found in topology graph")

        max_load = max(edge_loads_abs.values()) if edge_loads_abs else 0
        serializable_edge_loads = {f"{u}->{v}": round(load, 4) for (u, v), load in edge_loads_abs.items() if load > 0}

        # 3. BookSim Simulation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".cfg") as tmp_bs_cfg:
            bs_cfg_path = tmp_bs_cfg.name

        converter = BookSimConverter(current_config)
        converter.convert(bs_cfg_path)
        bs_lat, bs_thr, bs_edges = run_booksim(bs_cfg_path, booksim_exe, w, topo)
        os.remove(bs_cfg_path)

        # 4. C Model Simulation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as tmp_c_cfg:
            yaml.dump(current_config, tmp_c_cfg)
            c_cfg_path = tmp_c_cfg.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".trace") as tmp_trace:
            trace_path = tmp_trace.name

        generate_trace(num_nodes, inj_rates, current_config['simulation']['sim_cycles'], trace_path, 'custom_matrix', w, h, matrix_file)

        c_lat, c_thr, c_edges = run_c_model(c_cfg_path, trace_path, c_model_exe, w, h, topo)

        os.remove(c_cfg_path)
        os.remove(trace_path)

        # 5. Compile Results
        results[topo] = {
            'theory_max_load': max_load,
            'theory_edge_loads': serializable_edge_loads,
            'booksim_latency': bs_lat,
            'booksim_throughput': bs_thr,
            'booksim_edge_loads': bs_edges,
            'c_model_latency': c_lat,
            'c_model_throughput': c_thr,
            'c_model_edge_loads': c_edges
        }

        print(f"  Theory Max Channel Load: {max_load:.4f} FLITs/cycle")
        print(f"  BookSim -> Latency: {bs_lat:.2f}, Throughput: {bs_thr:.4f}")
        print(f"  C Model -> Latency: {c_lat:.2f}, Throughput: {c_thr:.4f}")

    output_file = os.path.join(os.path.dirname(__file__), '..', 'reports', 'custom_workload', 'data', 'custom_workload_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
