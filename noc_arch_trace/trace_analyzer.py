import sys

def analyze_trace(filepath):
    total_packets = 0
    src_counts = {}
    dst_counts = {}

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                # 忽略空行或註解 (Ignore empty lines or comments)
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                src = parts[0]
                dst = parts[1]

                total_packets += 1
                # 統計來源分佈 (Count source distribution)
                src_counts[src] = src_counts.get(src, 0) + 1
                # 統計目的分佈 (Count destination distribution)
                dst_counts[dst] = dst_counts.get(dst, 0) + 1

        print(f"--- Trace Analysis Report (Trace 分析報告): {filepath} ---")
        print(f"Total Packets (總封包數): {total_packets}")
        print("\nSource Distribution (來源分佈):")
        for src, count in sorted(src_counts.items(), key=lambda x: int(x[0])):
            print(f"  Node {src}: {count}")

        print("\nDestination Distribution (目的分佈):")
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
