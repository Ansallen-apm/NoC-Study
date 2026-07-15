#!/usr/bin/env python3
import subprocess
import os
import re
import sys

def run_sim(config, trace, noc_sim_path):
    result = subprocess.run(
        [noc_sim_path, config, trace],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(noc_sim_path)
    )
    return result.stdout, result.returncode

def parse_output(output, returncode):
    metrics = {"returncode": returncode}

    avg_lat = re.search(r"Average Latency: ([\d.]+) cycles", output)
    if avg_lat:
        metrics["avg_latency"] = float(avg_lat.group(1))

    max_lat = re.search(r"Max Latency: (\d+) cycles", output)
    if max_lat:
        metrics["max_latency"] = int(max_lat.group(1))

    router_rx = re.findall(r"Router (\d+) received (\d+) flits\.", output)
    metrics["received_flits"] = {int(r): int(f) for r, f in router_rx}

    port_active = re.findall(r"Router (\d+) Port (\d+) ActiveCycles: (\d+)", output)
    metrics["port_active_cycles"] = {}
    for r, p, c in port_active:
        r, p, c = int(r), int(p), int(c)
        if r not in metrics["port_active_cycles"]:
            metrics["port_active_cycles"][r] = {}
        metrics["port_active_cycles"][r][p] = int(c)

    return metrics

def compare_metrics(name, golden, actual):
    if golden["returncode"] != actual["returncode"]:
        print(f"[{name}] Return code mismatch: {golden['returncode']} != {actual['returncode']}")
        return False

    if abs(golden["avg_latency"] - actual["avg_latency"]) > 0.001:
        print(f"[{name}] Avg latency mismatch: {golden['avg_latency']} != {actual['avg_latency']}")
        return False

    if golden["max_latency"] != actual["max_latency"]:
        print(f"[{name}] Max latency mismatch: {golden['max_latency']} != {actual['max_latency']}")
        return False

    if golden["received_flits"] != actual["received_flits"]:
        print(f"[{name}] Received flits mismatch: {golden['received_flits']} != {actual['received_flits']}")
        return False

    if golden["port_active_cycles"] != actual["port_active_cycles"]:
        print(f"[{name}] Port active cycles mismatch: {golden['port_active_cycles']} != {actual['port_active_cycles']}")
        return False

    return True

def main():
    topologies = ["mesh", "torus", "ring"]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, "golden")
    noc_sim_path = os.path.abspath(os.path.join(script_dir, "..", "noc_sim"))

    all_passed = True
    for topo in topologies:
        # Paths relative to the noc_sim binary's CWD
        config = os.path.join("tests", "golden", f"{topo}.yaml")
        trace = os.path.join("tests", "golden", f"{topo}.trace")
        golden_out = os.path.join(base_dir, f"{topo}.out")

        with open(golden_out, "r") as f:
            golden_text = f.read()

        golden_metrics = parse_output(golden_text, 0) # Assuming golden run was success (0)

        actual_text, actual_rc = run_sim(config, trace, noc_sim_path)
        actual_metrics = parse_output(actual_text, actual_rc)

        if compare_metrics(topo, golden_metrics, actual_metrics):
            print(f"[{topo}] PASS")
        else:
            print(f"[{topo}] FAIL")
            all_passed = False

    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
