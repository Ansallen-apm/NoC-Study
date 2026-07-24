import re

with open('scripts/run_custom_workload_dse.py', 'r') as f:
    content = f.read()

# Fix BookSim ring router regex
new_content = content.replace(
r'''                match = re.search(r"router_(\d+)_(\d+)", line)
                if match:
                    y, x = int(match.group(1)), int(match.group(2))
                    current_router = y * width + x if topo != 'ring' else x''',
r'''                match = re.search(r"router_(\d+)(?:_(\d+))?", line)
                if match:
                    if match.group(2): # 2D router
                        y, x = int(match.group(1)), int(match.group(2))
                        current_router = y * width + x
                    else: # 1D ring router
                        current_router = int(match.group(1))''')

with open('scripts/run_custom_workload_dse.py', 'w') as f:
    f.write(new_content)
