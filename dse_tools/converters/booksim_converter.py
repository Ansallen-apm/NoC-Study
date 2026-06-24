import sys
import os
from .base_converter import ConfigConverterBase

class BookSimConverter(ConfigConverterBase):
    """
    負責將 NoC_config.yaml 轉換為 BookSim 專用的 key=value 設定檔格式。
    """
    def convert(self, output_filepath):
        arch = self.config.get('architecture', {})
        sim = self.config.get('simulation', {})
        booksim_overrides = self.config.get('simulators', {}).get('booksim', {})

        topo_type = arch.get('topology', 'mesh').lower()
        routing = arch.get('routing', 'xy').lower()

        # BookSim models a ring as a 1D torus
        bs_topology = "torus" if topo_type == "ring" else topo_type
        dimension_n = 1 if topo_type == "ring" else 2

        # Default mapping for routing
        if routing == 'xy':
            bs_routing = 'dim_order'
        else:
            bs_routing = routing

        traffic_pattern = sim.get('traffic_pattern', 'uniform')

        # 對應 BookSim 的參數名稱
        bs_config = {
            # Topology
            "topology": bs_topology,
            "k": arch.get('width', 4),  # Mesh size / Nodes in ring
            "n": dimension_n,           # Dimension (2D or 1D)
            "routing_function": bs_routing,

            # Flow Control & Buffers
            "num_vcs": arch.get('num_vcs', 1),
            "vc_buf_size": arch.get('buffer_size', 8),

            # Traffic
            "traffic": traffic_pattern,
            "injection_rate": sim.get('injection_rate', 0.1),
            "packet_size": arch.get('packet_size', 1),

            # Simulation
            "sim_type": "latency",
            "warmup_periods": 3, # BookSim uses sample periods, simplify here
            "max_samples": 10,
            "sample_period": int(sim.get('sim_cycles', 5000) / 10),

            # Overrides
            **booksim_overrides
        }

        # Handle custom traffic matrix by approximating it as a hotspot pattern in BookSim
        if traffic_pattern == 'custom_matrix':
            matrix_file = sim.get('custom_matrix_file')
            if matrix_file and os.path.exists(matrix_file):
                import csv
                try:
                    num_nodes = arch.get('width', 4) * (arch.get('height', 4) if bs_topology != 'torus' or dimension_n > 1 else 1)
                    if bs_topology == 'torus' and dimension_n == 1:
                         num_nodes = arch.get('width', 4)

                    # Compute the sum of incoming probabilities for each node across the entire matrix
                    dst_weights = [0.0] * num_nodes
                    with open(matrix_file, 'r') as f:
                        reader = csv.reader(f)
                        next(reader) # Skip header
                        for row in reader:
                            for dst, prob in enumerate(row):
                                dst_weights[dst] += float(prob)

                    # Find significant hotspots (e.g., nodes that receive more traffic than average)
                    average_weight = sum(dst_weights) / num_nodes if num_nodes > 0 else 0
                    hotspots = []
                    rates = []
                    for i, weight in enumerate(dst_weights):
                        # If a node receives significant traffic, add it as a hotspot
                        # We use > 0 instead of > average to capture all intended destinations
                        # but we scale by weight
                        if weight > 0.001:
                            hotspots.append(i)
                            rates.append(int(weight * 100)) # Convert to integer rates

                    if hotspots:
                        bs_config['traffic'] = 'hotspot'
                        # BookSim syntax for array is {1, 2, 3}
                        bs_config['hotspots'] = "{" + ",".join(map(str, hotspots)) + "}"
                        bs_config['hotspot_rates'] = "{" + ",".join(map(str, rates)) + "}"
                    else:
                        bs_config['traffic'] = 'uniform'
                except Exception as e:
                    print(f"Warning: Failed to parse custom matrix for BookSim conversion: {e}. Falling back to uniform.")
                    bs_config['traffic'] = 'uniform'
            else:
                print("Warning: custom_matrix_file not found. Falling back to uniform for BookSim.")
                bs_config['traffic'] = 'uniform'

        with open(output_filepath, 'w', encoding='utf-8') as f:
            for key, value in bs_config.items():
                f.write(f"{key} = {value};\n")
