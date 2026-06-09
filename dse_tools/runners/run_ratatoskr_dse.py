import sys
import os
import json
import subprocess
import yaml
import uuid
import glob

from converters.ratatoskr_converter import RatatoskrConverter

def cleanup_files(*files_and_patterns):
    for fp in files_and_patterns:
        for f in glob.glob(fp):
            try:
                os.remove(f)
            except OSError:
                pass

def run_ratatoskr(config):
    uid = str(uuid.uuid4())[:8]
    yaml_name = f"temp_{uid}.yaml"
    net_name = f"net_{uid}.xml"
    sim_name = f"sim_{uid}.xml"
    report_name = f"report_{uid}"

    with open(yaml_name, "w") as f:
        yaml.dump(config, f)

    conv = RatatoskrConverter(yaml_name)
    conv.generate_config(sim_name, net_name, report_name)

    ratatoskr_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "third_party", "ratatoskr", "simulator", "sim")

    try:
        subprocess.run([ratatoskr_path, sim_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        cleanup_files(yaml_name, net_name, sim_name, f"{report_name}*")
        return float('inf'), 0

    avg_latency = float('inf')
    try:
        with open(f"{report_name}_Performance.csv", "r") as f:
            for l in f:
                if "avgPacketLat" in l:
                    avg_latency = float(l.split(",")[1].strip())
    except FileNotFoundError:
        pass

    cleanup_files(yaml_name, net_name, sim_name, f"{report_name}*")
    import shutil
    for d in ["BuffUsage", "VCUsage"]:
        if os.path.exists(d) and os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)

    return avg_latency, 0

if __name__ == "__main__":
    c = {
        "topology": "mesh",
        "mesh_width": 4,
        "mesh_height": 4,
        "routing_algorithm": "xy",
        "traffic_pattern": "uniform",
        "injection_rate": 0.05,
        "num_vcs": 2,
        "buffer_size": 4,
        "simulation_cycles": 10000,
        "packet_size": 1
    }
    lat, tp = run_ratatoskr(c)
    print(f"Ratatoskr Latency: {lat}")
