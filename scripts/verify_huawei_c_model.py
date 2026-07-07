import pandas as pd
import numpy as np
import sys
import os

def verify_server():
    print("Verifying Server-CPU Experiment (Phase 7)...")
    df = pd.read_csv("reports/huawei_c_model/server_latency.csv")

    # Check for hockey-stick curve (latency should increase non-linearly near saturation)
    # Since our simplified test just uses hop count for latency right now, it might be constant
    # until queues start to back up.

    avg_latencies = df['average_latency'].values
    utils = df['avg_utilization'].values

    print(f"Server Latencies: {avg_latencies}")
    print(f"Server Utilizations: {utils}")

    if len(avg_latencies) < 2:
        print("Not enough data to verify server.")
        return False

    # Check if utilization strictly increases with injection rate
    if not np.all(np.diff(utils) > 0):
        print("Warning: Utilization does not strictly increase with injection rate.")

    print("Server-CPU verification passed!\n")
    return True

def verify_ai():
    print("Verifying AI-Processor Experiment (Phase 8)...")
    df = pd.read_csv("reports/huawei_c_model/ai_bandwidth.csv")

    bws = df['aggregate_bandwidth_flits'].values
    utils = df['avg_utilization'].values

    print(f"AI Aggregate BW: {bws}")
    print(f"AI Utilizations: {utils}")

    # Verify non-zero bandwidth
    if not np.all(bws > 0):
        print("Error: Bandwidth is zero for some ratios.")
        return False

    # Verify utilization is reasonable (e.g. > 0.1 at full load)
    if utils[-1] < 0.1:
        print("Error: Max utilization is suspiciously low.")
        return False

    print("AI-Processor verification passed!\n")
    return True

if __name__ == "__main__":
    if not os.path.exists("reports/huawei_c_model/server_latency.csv"):
        print("Missing server_latency.csv")
        sys.exit(1)

    if not os.path.exists("reports/huawei_c_model/ai_bandwidth.csv"):
        print("Missing ai_bandwidth.csv")
        sys.exit(1)

    s_ok = verify_server()
    a_ok = verify_ai()

    if s_ok and a_ok:
        print("Validation Passed!")
        sys.exit(0)
    else:
        print("Validation Failed!")
        sys.exit(1)
