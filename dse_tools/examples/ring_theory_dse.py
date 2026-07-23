import sys
import os
import json
import networkx as nx

def analyze_ring_theory(widths):
    results = {}
    channel_bandwidth = 32 # bits per cycle

    for width in widths:
        # Generate Ring (1D Torus)
        # We use a standard graph and add edges to form a ring
        G = nx.cycle_graph(width)

        # 1. Calculate Average Hops
        path_lengths = dict(nx.shortest_path_length(G))
        total_hops = 0
        num_paths = 0
        for src in G.nodes():
            for dst in G.nodes():
                if src != dst:
                    total_hops += path_lengths[src][dst]
                    num_paths += 1
        avg_hops = total_hops / num_paths if num_paths > 0 else 0

        # 2. Calculate Bisection Bandwidth
        # A ring is cut into two halves by cutting 2 links.
        # Since links are bidirectional in a typical NoC, cutting the ring severs 4 directed channels.
        bisection_bw = 4 * channel_bandwidth

        # 3. Calculate Maximum Injection Rate (Theoretical Ceiling)
        # In a uniform random traffic on a bidirectional ring, the max channel load is roughly:
        # Load_max = (N^2 - 1) / (8 * N)  for odd N
        # Load_max = N / 8                for even N
        # The theoretical max injection rate per node is 1 / Load_max
        if width % 2 == 0:
            load_max = width / 8.0
        else:
            load_max = (width**2 - 1) / (8.0 * width)

        max_injection_rate = 1.0 / load_max if load_max > 0 else 1.0

        results[f"Ring_{width}"] = {
            "nodes": width,
            "average_hops": round(avg_hops, 4),
            "bisection_bandwidth_bps": bisection_bw,
            "theoretical_max_injection_rate": round(max_injection_rate, 4),
            "max_channel_load_per_packet": round(load_max, 4)
        }

    return results

def main():
    print("啟動 Ring DSE 理論分析...")
    widths = [4, 6, 7, 8, 10, 12, 16]

    results = analyze_ring_theory(widths)

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports", "uniform_dse", "data", "report_theory_ring.json"), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("理論分析完成，已匯出至 reports/report_theory_ring.json")

if __name__ == "__main__":
    main()
