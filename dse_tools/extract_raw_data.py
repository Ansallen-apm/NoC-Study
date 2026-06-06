import json

with open('dse_tools/report/verification_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

print("=== Raw Data for Correlation ===")
print(f"{'Topology':<10} | {'Nodes':<6} | {'Theory Rate (X)':<16} | {'Booksim Rate (Y)':<16}")
print("-" * 55)

for r in results:
    topo = r['topology']
    nodes = r['nodes']
    t_rate = r['theory_max_rate']
    b_rate = r['booksim_actual_sat_rate']
    print(f"{topo:<10} | {nodes:<6} | {t_rate:<16.4f} | {b_rate:<16.4f}")
