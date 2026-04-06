import sys
import re
import matplotlib.pyplot as plt

def analyze_metrics(log_file):
    try:
        with open(log_file, "r") as f:
            log_data = f.read()
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found.")
        sys.exit(1)

    # Use regex to extract numeric values based on the metric tags
    latency_values = [float(x) for x in re.findall(r'End-to-End Latency: ([0-9.]+)', log_data)]
    throughput_values = [float(x) for x in re.findall(r'Throughput: ([0-9.]+)', log_data)]
    verification_values = [float(x) for x in re.findall(r'Verification Time: ([0-9.]+)', log_data)]
    reconciliation_values = [float(x) for x in re.findall(r'Reconciliation Time: ([0-9.]+)', log_data)]

    # A. Latency Graph
    if latency_values:
        plt.figure()
        plt.plot(range(len(latency_values)), latency_values, marker='o')
        plt.title('End-to-End Latency over Time')
        plt.xlabel('Sample Index')
        plt.ylabel('Latency (ms)')
        plt.grid(True)
        plt.savefig('latency.png')
        plt.close()
        print(f"Saved latency.png with {len(latency_values)} data points.")

    # B. Throughput Graph
    if throughput_values:
        plt.figure()
        plt.plot(range(len(throughput_values)), throughput_values, marker='o')
        plt.title('Throughput over Time')
        plt.xlabel('Sample Index')
        plt.ylabel('Throughput (packets/sec)')
        plt.grid(True)
        plt.savefig('throughput.png')
        plt.close()
        print(f"Saved throughput.png with {len(throughput_values)} data points.")

    # C. Verification Time Graph
    if verification_values:
        plt.figure()
        plt.plot(range(len(verification_values)), verification_values, marker='o')
        plt.title('Verification Time per Batch')
        plt.xlabel('Sample Index')
        plt.ylabel('Verification Time (ms)')
        plt.grid(True)
        plt.savefig('verification.png')
        plt.close()
        print(f"Saved verification.png with {len(verification_values)} data points.")

    # D. Reconciliation Time Graph (Bar Chart)
    if reconciliation_values:
        plt.figure()
        plt.bar(range(len(reconciliation_values)), reconciliation_values)
        plt.title('Reconciliation Time per Event')
        plt.xlabel('Event Index')
        plt.ylabel('Reconciliation Time (sec)')
        plt.grid(True, axis='y')
        plt.savefig('reconciliation.png')
        plt.close()
        print(f"Saved reconciliation.png with {len(reconciliation_values)} data points.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_metrics.py <logfile>")
        print("Example: python analyze_metrics.py fog.log")
        sys.exit(1)
    
    analyze_metrics(sys.argv[1])
    print("Metrics analysis complete.")
