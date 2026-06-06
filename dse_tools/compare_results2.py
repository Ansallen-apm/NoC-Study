import json

with open('dse_tools/report/verification_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

print(f"{'Topology':<10} | {'Nodes':<5} | {'Theory Hops':<12} | {'Booksim Latency':<15}")
print("-" * 55)

for r in results:
    topo = r['topology']
    nodes = r['nodes']
    theory_hops = r['theory_avg_hops']
    lat = r['booksim_zero_load_lat']
    print(f"{topo:<10} | {nodes:<5} | {theory_hops:<12.4f} | {lat:<15.4f}")
