import json

with open('dse_tools/report/verification_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

print(f"{'Topology':<10} | {'Nodes':<5} | {'Theory Rate (X)':<16} | {'Booksim Rate (Y)':<16}")
print("-" * 55)

for r in results:
    topo = r['topology']
    nodes = r['nodes']
    t_rate = r['theory_max_rate']
    b_rate = r['booksim_actual_sat_rate']
    if topo == 'ring' and nodes in [4, 5, 6, 7, 8]:
        print(f"{topo:<10} | {nodes:<5} | {t_rate:<16.4f} | {b_rate:<16.4f}")
