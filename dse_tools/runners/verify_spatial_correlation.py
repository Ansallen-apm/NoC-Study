import sys
import os
import subprocess
import re
import numpy as np
import tempfile
from noc_python_model.topology import generate_mesh_topology
from noc_python_model.metrics import analyze_channel_load

# BookSim Port Mapping for Mesh:
# 0 = Right (+x)
# 1 = Left (-x)
# 2 = Down (+y)
# 3 = Up (-y)
# 4 = Local

def get_neighbor(router_id, port, k):
    x = router_id % k
    y = router_id // k
    if port == 0: # Right (+x)
        return y * k + (x + 1) if x < k - 1 else -1
    elif port == 1: # Left (-x)
        return y * k + (x - 1) if x > 0 else -1
    elif port == 2: # Down (+y)
        return (y + 1) * k + x if y < k - 1 else -1
    elif port == 3: # Up (-y)
        return (y - 1) * k + x if y > 0 else -1
    return -1

def verify_mesh_spatial(k=4):
    config_content = f"""
topology = mesh;
k = {k};
n = 2;
routing_function = dim_order;
traffic = uniform;
injection_rate = 0.1;
sample_period = 100000;
sim_type = latency;
print_activity = 1;
"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write(config_content)
        temp_config_path = f.name

    print(f"Running Booksim for {k}x{k} Mesh...")

    booksim_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "third_party", "booksim", "src", "booksim")

    try:
        result = subprocess.run(
            [booksim_path, temp_config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        out_lines = result.stdout.splitlines()
    finally:
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)

    actual_edge_loads = {}
    in_monitor = False
    router_id = 0

    for l in out_lines:
        if "switchMonitor" in l:
            in_monitor = True
            m = re.search(r"router_(\d+)_(\d+)", l)
            if m:
                router_y = int(m.group(1))
                router_x = int(m.group(2))
                router_id = router_y * k + router_x
        elif "Inputs=" in l and in_monitor:
            idx = l.find("[")
            if idx != -1:
                l = l[idx:]
            else:
                continue

        if in_monitor and "->" in l:
            parts = l.split("]")
            io_str = parts[0].replace("[", "").strip()
            i, o = io_str.split("->")
            in_port = int(i.strip())
            out_port = int(o.strip())

            val_str = parts[1].strip()
            if ":" in val_str:
                count = int(val_str.split(":")[1])
                # We want router-to-router edges. So we ONLY ignore out_port == 4 (ejection).
                # Local injection (in_port == 4) must be counted!
                if count > 0 and out_port != 4:
                    dst_node = get_neighbor(router_id, out_port, k)
                    if dst_node != -1:
                        edge_str = f"{router_id}->{dst_node}"
                        if edge_str not in actual_edge_loads:
                            actual_edge_loads[edge_str] = 0
                        actual_edge_loads[edge_str] += count

        elif in_monitor and not l.strip():
            in_monitor = False

    G = generate_mesh_topology(k, k)
    res = analyze_channel_load(G, 'xy', 'uniform')
    theory_edge_loads = res['all_edge_loads']

    X = []
    Y = []

    print(f"--- Edge Loads Comparison ({k}x{k} Mesh) ---")
    print(f"{'Edge':<8} | {'Theory (X)':<12} | {'Actual Count (Y)':<15}")
    for edge, t_load in theory_edge_loads.items():
        if t_load > 0:
            a_load = actual_edge_loads.get(edge, 0)
            X.append(t_load)
            Y.append(a_load)
            print(f"{edge:<8} | {t_load:<12.4f} | {a_load:<15}")

    corr = np.corrcoef(X, Y)[0,1]
    print(f"\nSpatial Correlation: {corr:.4f} (Expected near 1.0)")

if __name__ == "__main__":
    verify_mesh_spatial(4)
