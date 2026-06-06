import yaml
import json

with open("dse_tools/config/verification_sweep.yaml", "r") as f:
    config = yaml.safe_load(f)

print("=== verification_sweep.yaml Variables (Variables with >1 option) ===")
# DSE Lists
for key, value in config.items():
    if isinstance(value, list) and len(value) > 1:
        print(f"{key}: {value}")
    elif isinstance(value, dict):
        # check nested lists
        has_multi = False
        for sub_k, sub_v in value.items():
             if isinstance(sub_v, list) and len(sub_v) > 1:
                 has_multi = True
        if has_multi:
             print(f"{key}: {value}")
