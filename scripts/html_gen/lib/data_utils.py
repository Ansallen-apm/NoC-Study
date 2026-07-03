import json
import os

def load_json(filepath, default_val=None):
    if not os.path.exists(filepath):
        print(f"Warning: Data file {filepath} not found.")
        return default_val if default_val is not None else {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
