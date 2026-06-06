import json
import numpy as np

def calculate_error(theory, actual):
    if theory == 0:
        return float('inf') if actual != 0 else 0.0
    return abs(theory - actual) / actual * 100 if actual != 0 else float('inf')

with open('dse_tools/report/verification_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

print(f"{'Topology':<15} | {'Dim':<5} | {'Theory MaxRate':<15} | {'Booksim SatRate':<15} | {'Error (%)':<10}")
print("-" * 70)

for r in results:
    topo = r['topology']
    dim = r['dim']
    theory_rate = r['theory_max_rate']
    actual_rate = r['booksim_actual_sat_rate']
    err = calculate_error(theory_rate, actual_rate)
    print(f"{topo:<15} | {dim:<5} | {theory_rate:<15.4f} | {actual_rate:<15.4f} | {err:<10.2f}")
