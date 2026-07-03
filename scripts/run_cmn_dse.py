import sys
import os
import yaml
import json
import subprocess
import copy
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from dse_tools.converters.booksim_converter import BookSimConverter
from dse_tools.runners.run_c_model_dse import generate_trace
import tempfile
from noc_python_model.topology import generate_mesh_topology, generate_torus_topology, generate_ring_topology
from noc_python_model.metrics import calculate_bisection_bandwidth, calculate_average_hop_count

C_MODEL_EXEC = os.path.join(ROOT_DIR, 'noc_c_model', 'noc_sim')
BOOKSIM_EXEC = os.path.join(ROOT_DIR, 'third_party', 'booksim', 'src', 'booksim')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports', 'cmn_dse')

os.makedirs(REPORTS_DIR, exist_ok=True)

topologies = [
    {'name': 'ring', 'width': 16, 'height': 1},
    {'name': 'mesh', 'width': 4, 'height': 4},
    {'name': 'torus', 'width': 4, 'height': 4}
]
frequencies = [2.5, 1.5]
vcs_list = [1, 2]
flit_size = 1
buffer_size = 4
data_width_bytes = 64
sim_cycles = 1000
injection_rate = 1.0

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
    bisection_bw_GBps = (bisection_bw_bits * freq_ghz * 1e9) / (8 * 1e9)
    avg_hops = calculate_average_hop_count(graph)

    return {
        'bisection_bw_GBps': bisection_bw_GBps,
        'avg_hops': avg_hops
    }

def run_c_model(topo, freq_ghz, num_vcs):
    config = {
        'architecture': {
            'topology': topo['name'],
            'width': topo['width'],
            'height': topo['height'],
            'routing': 'xy' if topo['name'] == 'mesh' else 'dim_order',
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

        # Total Throughput * data_width_bytes * freq_GHz / num_nodes
        bw_GBps_per_node = (throughput * flit_size * data_width_bytes * freq_ghz) / num_nodes

        os.remove(yaml_path)
        os.remove(trace_path)

        return {
            'latency': latency,
            'throughput_packets_per_cycle': throughput,
            'bw_GBps_per_node': bw_GBps_per_node,
            'deadlock': deadlock
        }
    except Exception as e:
        return {'error': str(e), 'deadlock': True}

def run_booksim(topo, freq_ghz, num_vcs):
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
        throughput_flits_per_node = 0.0

        for line in output.split('\n'):
            match_lat = re.search(r'Packet latency average = ([\d\.]+)', line)
            if match_lat: latency = float(match_lat.group(1))

            # accepted flits/cycle/node
            match_tpt = re.search(r'Accepted flit rate.*?= ([\d\.]+)', line)
            if match_tpt: throughput_flits_per_node = float(match_tpt.group(1))

        bw_GBps_per_node = throughput_flits_per_node * data_width_bytes * freq_ghz

        os.remove(cfg_path)
        return {
            'latency': latency,
            'throughput_flits_per_cycle_per_node': throughput_flits_per_node,
            'bw_GBps_per_node': bw_GBps_per_node,
            'deadlock': deadlock
        }
    except Exception as e:
        return {'error': str(e), 'deadlock': True}

results = []

for vcs in vcs_list:
    for freq in frequencies:
        for topo in topologies:
            print(f"Running DSE for {topo['name']} at {freq} GHz with VC={vcs}...")
            py_res = run_python_model(topo, freq)
            c_res = run_c_model(topo, freq, vcs)
            bs_res = run_booksim(topo, freq, vcs)

            res = {
                'topology': topo['name'],
                'frequency_GHz': freq,
                'vcs': vcs,
                'python': py_res,
                'c_model': c_res,
                'booksim': bs_res
            }
            results.append(res)

os.makedirs(os.path.join(REPORTS_DIR, 'data'), exist_ok=True)
with open(os.path.join(REPORTS_DIR, 'data', 'data.json'), 'w') as f:
    json.dump(results, f, indent=4)

print("DSE run complete. Data saved to reports/cmn_dse/data/data.json.")
