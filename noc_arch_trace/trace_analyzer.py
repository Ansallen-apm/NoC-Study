import sys

def analyze_trace(filepath):
    total_packets = 0
    src_counts = {}
    dst_counts = {}

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                src = parts[0]
                dst = parts[1]

                total_packets += 1
                src_counts[src] = src_counts.get(src, 0) + 1
                dst_counts[dst] = dst_counts.get(dst, 0) + 1

        print(f"--- Trace Analysis Report: {filepath} ---")
        print(f"Total Packets: {total_packets}")
        print("\nSource Distribution:")
        for src, count in sorted(src_counts.items(), key=lambda x: int(x[0])):
            print(f"  Node {src}: {count}")

        print("\nDestination Distribution:")
        for dst, count in sorted(dst_counts.items(), key=lambda x: int(x[0])):
            print(f"  Node {dst}: {count}")

    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 trace_analyzer.py <trace_file>")
    else:
        analyze_trace(sys.argv[1])
