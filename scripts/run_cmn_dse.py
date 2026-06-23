import sys
import os
import yaml
import json
import subprocess
import copy
import re

# Set up paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from dse_tools.converters.booksim_converter import BookSimConverter
from dse_tools.runners.run_c_model_dse import generate_trace
import tempfile
from noc_python_model.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
from noc_python_model.metrics import calculate_bisection_bandwidth, calculate_average_hop_count

C_MODEL_EXEC = os.path.join(ROOT_DIR, 'noc_c_model', 'noc_sim')
BOOKSIM_EXEC = os.path.join(ROOT_DIR, 'third_party', 'booksim', 'src', 'booksim')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports', 'CMN_DSE')

os.makedirs(REPORTS_DIR, exist_ok=True)

# Configurations to sweep
topologies = [
    {'name': 'ring', 'width': 16, 'height': 1},
    {'name': 'mesh', 'width': 4, 'height': 4},
    {'name': 'torus', 'width': 4, 'height': 4}
]
frequencies = [2.5, 1.5] # GHz
flit_size = 1 # packet size
buffer_size = 4
num_vcs = 1
data_width_bytes = 64
sim_cycles = 1000
injection_rate = 1.0 # full load

def run_python_model(topo, freq_ghz):
    name = topo['name']
    w, h = topo['width'], topo['height']
    if name == 'ring':
        graph = generate_ring_topology(w)
    elif name == 'mesh':
        graph = generate_mesh_topology(w, h)
    elif name == 'torus':
        graph = generate_torus_topology(w, h)

    bisection_bw_bits = calculate_bisection_bandwidth(graph, channel_bandwidth_bits=data_width_bytes * 8)

    # Python metric only provides BW in bits/cycle. We convert to GB/s.
    # GB/s = Bisection_BW_bits * freq_GHz / 8 / 1024 / 1024 ... wait,
    # 1 GB = 10**9 Bytes or 2**30 Bytes? Usually GB/s is 10**9 for network, or 1024**3.
    # Let's use 1 GB = 10**9 Bytes
    bisection_bw_GBps = (bisection_bw_bits * freq_ghz * 1e9) / (8 * 1e9)

    avg_hops = calculate_average_hop_count(graph)

    return {
        'bisection_bw_GBps': bisection_bw_GBps,
        'avg_hops': avg_hops
    }

def run_c_model(topo, freq_ghz):
    # 1. Create YAML
    config = {
        'architecture': {
            'topology': topo['name'],
            'width': topo['width'],
            'height': topo['height'],
            'routing': 'xy' if topo['name'] == 'mesh' else 'dim_order', # C model routing
            'packet_size': flit_size,
            'buffer_size': buffer_size,
            'num_vcs': num_vcs,
            'flit_width_bits': data_width_bytes * 8,
            'frequency_mhz': int(freq_ghz * 1000)
        },
        'simulation': {
            'traffic_pattern': 'uniform',
            'sim_cycles': sim_cycles,
            'injection_rate': injection_rate
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as f:
        yaml.dump(config, f)
        yaml_path = f.name

    num_nodes = topo['width'] * topo['height']
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
        trace_path = f.name

    generate_trace(num_nodes, injection_rate, sim_cycles, trace_path, 'uniform', topo['width'], topo['height'])

    try:
        cmd = [C_MODEL_EXEC, yaml_path, trace_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = result.stdout

        # Parse output
        latency = float('inf')
        throughput = 0.0
        deadlock = False

        if "Deadlock detected" in output or "Deadlock" in output:
            deadlock = True

        for line in output.split('\n'):
            if "Average Latency:" in line:
                match = re.search(r'Average Latency:\s*([\d\.]+)', line)
                if match: latency = float(match.group(1))
            elif "Total Throughput:" in line:
                match = re.search(r'Total Throughput:\s*([\d\.]+)', line)
                if match: throughput = float(match.group(1))

        # Calculate BW GB/s
        # Throughput = flits/cycle/node ? Wait, noc_c_model output:
        # Total Throughput: 0.123 packets/cycle
        # We need GB/s = Total Throughput * packet_size_flits * data_width_bytes * freq_GHz
        bw_GBps = throughput * flit_size * data_width_bytes * freq_ghz

        # Cleanup
        os.remove(yaml_path)
        os.remove(trace_path)

        return {
            'latency': latency,
            'throughput_packets_per_cycle': throughput,
            'bw_GBps': bw_GBps,
            'deadlock': deadlock
        }
    except Exception as e:
        return {'error': str(e), 'deadlock': True}

def run_booksim(topo, freq_ghz):
    config = {
        'architecture': {
            'topology': topo['name'],
            'width': topo['width'],
            'height': topo['height'],
            'routing': 'xy' if topo['name'] == 'mesh' else 'dim_order',
            'packet_size': flit_size,
            'buffer_size': buffer_size,
            'num_vcs': num_vcs,
        },
        'simulation': {
            'traffic_pattern': 'uniform',
            'sim_cycles': sim_cycles,
            'injection_rate': injection_rate
        }
    }

    converter = BookSimConverter(config)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".cfg") as f:
        cfg_path = f.name
    converter.convert(cfg_path)

    try:
        cmd = [BOOKSIM_EXEC, cfg_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr

        deadlock = "deadlock" in output.lower() or "aborted" in output.lower() or result.returncode != 0

        latency = float('inf')
        throughput = 0.0

        for line in output.split('\n'):
            match_lat = re.search(r'Packet latency average = ([\d\.]+)', line)
            if match_lat: latency = float(match_lat.group(1))

            # accepted flits/cycle/node
            match_tpt = re.search(r'Accepted flit rate.*?= ([\d\.]+)', line)
            if match_tpt: throughput = float(match_tpt.group(1)) * topo['width'] * topo['height']

        bw_GBps = throughput * data_width_bytes * freq_ghz

        os.remove(cfg_path)
        return {
            'latency': latency,
            'throughput_flits_per_cycle': throughput,
            'bw_GBps': bw_GBps,
            'deadlock': deadlock
        }
    except Exception as e:
        return {'error': str(e), 'deadlock': True}

results = []

for freq in frequencies:
    for topo in topologies:
        print(f"Running DSE for {topo['name']} at {freq} GHz...")
        py_res = run_python_model(topo, freq)
        c_res = run_c_model(topo, freq)
        bs_res = run_booksim(topo, freq)

        res = {
            'topology': topo['name'],
            'frequency_GHz': freq,
            'python': py_res,
            'c_model': c_res,
            'booksim': bs_res
        }
        results.append(res)

with open(os.path.join(REPORTS_DIR, 'data.json'), 'w') as f:
    json.dump(results, f, indent=4)

print("DSE run complete. Data saved to reports/CMN_DSE/data.json.")
