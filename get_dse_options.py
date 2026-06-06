import yaml
import json

with open("NoC_config.yaml", "r") as f:
    config = yaml.safe_load(f)

print("=== DSE Variables (Variables with >1 option) ===")
# Parameter Sweep
sweep = config.get("sweep_range", {})
if sweep:
    print(f"Injection Rate Sweep: {sweep.get('start')} to {sweep.get('end')} (step: {sweep.get('step')})")

# DSE Lists
for key, value in config.items():
    if isinstance(value, list) and len(value) > 1:
        print(f"{key}: {value}")
