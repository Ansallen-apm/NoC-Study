from .base_converter import ConfigConverterBase

class BookSimConverter(ConfigConverterBase):
    """
    負責將 NoC_config.yaml 轉換為 BookSim 專用的 key=value 設定檔格式。
    """
    def convert(self, output_filepath):
        arch = self.config.get('architecture', {})
        sim = self.config.get('simulation', {})
        booksim_overrides = self.config.get('simulators', {}).get('booksim', {})

        # 對應 BookSim 的參數名稱
        bs_config = {
            # Topology
            "topology": arch.get('topology', 'mesh'),
            "k": arch.get('width', 4),  # Mesh size
            "n": 2,                     # Dimension (2D)
            "routing_function": "dim_order" if arch.get('routing', 'xy') == 'xy' else arch.get('routing', 'xy'),

            # Flow Control & Buffers
            "num_vcs": arch.get('num_vcs', 1),
            "vc_buf_size": arch.get('buffer_size', 8),

            # Traffic
            "traffic": sim.get('traffic_pattern', 'uniform'),
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

        with open(output_filepath, 'w', encoding='utf-8') as f:
            for key, value in bs_config.items():
                f.write(f"{key} = {value};\n")
