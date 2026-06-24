import sys
import os
import unittest
import tempfile
import csv
import re
import subprocess
from collections import defaultdict

# Add the root directory to the python path so we can import dse_tools and noc_python_model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We will import the generator and converter functions once they are updated,
# but for the TDD test we first define what we expect them to do.
from dse_tools.runners.run_c_model_dse import generate_trace
from dse_tools.converters.booksim_converter import BookSimConverter

class TestTrafficConsistency(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for our test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.matrix_file = os.path.join(self.test_dir.name, "test_matrix.csv")
        self.trace_file = os.path.join(self.test_dir.name, "test.trace")
        self.booksim_config_file = os.path.join(self.test_dir.name, "booksim.cfg")

        # Create a simple 4x4 (16 nodes) matrix where:
        # Node 0 sends 80% to Node 15, 20% to Node 5
        # Node 1 sends 100% to Node 15
        # Node 2 sends 50% to Node 15, 50% to Node 11
        # Other nodes send 0% (or we just test the first few rows)
        self.num_nodes = 16

        with open(self.matrix_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([f"Dest_{i}" for i in range(self.num_nodes)])

            for src in range(self.num_nodes):
                row = [0.0] * self.num_nodes
                if src == 0:
                    row[15] = 0.8
                    row[5] = 0.2
                elif src == 1:
                    row[15] = 1.0
                elif src == 2:
                    row[15] = 0.5
                    row[11] = 0.5
                else:
                    # Others send to 15 to make it a heavy hotspot
                    row[15] = 1.0
                writer.writerow(row)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_c_model_trace_probabilities(self):
        """
        Verify that the generated trace file for C Model respects the probabilities
        defined in the custom matrix.
        """
        injection_rate = 1.0 # 100% injection to get lots of samples
        sim_cycles = 10000 # Enough cycles to get statistical significance
        width = 4
        height = 4

        # This will fail initially because generate_trace doesn't support 'custom_matrix' yet
        try:
            generate_trace(self.num_nodes, injection_rate, sim_cycles, self.trace_file, 'custom_matrix', width, height, custom_matrix_file=self.matrix_file)
        except TypeError:
             self.fail("generate_trace signature needs to be updated to accept custom_matrix_file")
        except NotImplementedError:
             self.fail("generate_trace needs to implement 'custom_matrix' logic")

        # Parse trace
        src_dst_counts = defaultdict(lambda: defaultdict(int))
        total_src_counts = defaultdict(int)

        with open(self.trace_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    parts = line.split()
                    src = int(parts[0])
                    dst = int(parts[1])
                    src_dst_counts[src][dst] += 1
                    total_src_counts[src] += 1

        # Check Node 0 probabilities (expect ~80% to 15, ~20% to 5)
        if total_src_counts[0] > 0:
            prob_0_to_15 = src_dst_counts[0][15] / total_src_counts[0]
            prob_0_to_5 = src_dst_counts[0][5] / total_src_counts[0]
            self.assertAlmostEqual(prob_0_to_15, 0.8, delta=0.05, msg=f"Node 0 -> 15 prob is {prob_0_to_15}, expected 0.8")
            self.assertAlmostEqual(prob_0_to_5, 0.2, delta=0.05, msg=f"Node 0 -> 5 prob is {prob_0_to_5}, expected 0.2")

        # Check Node 1 (100% to 15)
        if total_src_counts[1] > 0:
            prob_1_to_15 = src_dst_counts[1][15] / total_src_counts[1]
            self.assertAlmostEqual(prob_1_to_15, 1.0, delta=0.01)

        # Check Node 2 (50% to 15, 50% to 11)
        if total_src_counts[2] > 0:
            prob_2_to_15 = src_dst_counts[2][15] / total_src_counts[2]
            prob_2_to_11 = src_dst_counts[2][11] / total_src_counts[2]
            self.assertAlmostEqual(prob_2_to_15, 0.5, delta=0.05)
            self.assertAlmostEqual(prob_2_to_11, 0.5, delta=0.05)

    def test_booksim_converter_approximation(self):
        """
        Verify that BookSimConverter translates the matrix into a reasonable hotspot approximation.
        Since it can't map src->dst perfectly, it should identify the main hotspots across the whole matrix.
        """
        config = {
            'architecture': {'width': 4, 'height': 4},
            'simulation': {
                'traffic_pattern': 'custom_matrix',
                'custom_matrix_file': self.matrix_file
            }
        }

        converter = BookSimConverter(config)
        converter.convert(self.booksim_config_file)

        # Read the generated config
        with open(self.booksim_config_file, 'r') as f:
            content = f.read()

        # It should have set traffic to hotspot
        self.assertIn("traffic = hotspot;", content, "BookSim config did not set traffic to hotspot")

        # It should have identified Node 15 as the main hotspot, and maybe 5 and 11
        # The exact format might be hotspot = {15}; or something similar depending on implementation
        # But we expect 15 to be in the hotspot list.
        hotspot_match = re.search(r'hotspots\s*=\s*\{([^}]+)\}', content)
        if hotspot_match:
            hotspots = [int(x.strip()) for x in hotspot_match.group(1).split(',')]
            self.assertIn(15, hotspots, "Node 15 was not identified as a hotspot")
        else:
            self.fail("Could not find 'hotspots = {...}' array in BookSim config")

if __name__ == '__main__':
    unittest.main()
