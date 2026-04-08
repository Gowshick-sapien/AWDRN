# AWDRN: Autonomous Wildfire Detection & Rapid Response Network

The AWDRN project is a robust Edge/Fog Computing simulation that focuses heavily on secure data transmission, cryptography, decentralized trust, and scalable verification mechanisms. The architecture spans from a constrained edge device (Sensor) up to a centralized authority (Cloud), with a powerful intermediate gateway (Fog node) handling heavy compute.

## Architecture

The system is composed of four main containerized services:

1. **Sensor (`sensor_c`)**: 
   - A low-level C implementation for maximum efficiency.
   - Generates and signs telemetry using **Ed25519** (`libsodium`).
   - Uses a custom binary protocol to avoid JSON overhead and broadcasts data via UDP.

2. **Network Emulator (`network`)**:
   - Injects realistic network conditions.
   - Artificially drops roughly 20% of incoming packets.
   - Introduces random latency jitter (0-500ms) to simulate harsh, real-world wireless industrial environments.

3. **Fog Node (`fog`)**:
   - Acts as a zero-trust gateway. Strict Ed25519 signature verification against known public keys.
   - Protects against replay attacks by persisting counter states.
   - Stores verified traffic in a high-throughput SQLite database (WAL mode).
   - Generates deterministic Merkle Trees and extracts full mathematical Proofs for the parsed telemetry payload.

4. **Cloud Verification (`cloud`)**:
   - A massive stateless architecture using fractional verification via Merkle Proofs.
   - Efficient short-circuit execution: instantly rejects mathematically invalid payloads without parsing massive blocks.
   - Includes an explicit adversarial api (`/tamper`) to simulate compromised networks or faulty middleware.

## Features & Highlights

- **Cryptographic Security**: Ed25519 signatures from constrained edge up to Fog.
- **Data Integrity**: Merkle Proof-based stateless verification at the Cloud.
- **Resilience**: Realistic fault simulation and replay attack protection.
- **Monitoring**: Real-time Fog alerting (`🚨 CLOUD DETECTED DATA TAMPERING! 🚨`) when integrity is compromised.
- **Metrics Generation**: Includes an `analyze_metrics.py` tool to quickly visualize system performance, throughput, latency, and Merkle Proof reconciliation.

## Getting Started

### Prerequisites

- Docker
- Docker Compose
- Python 3.x (to run metrics extraction offline, optional)

### Running the System

To build and start the entire simulated network, run the following command in the root directory:

```bash
docker-compose up --build
```

The services will initialize in the following order and dependencies will naturally resolve:
1. `cloud` (Port: 8000)
2. `fog` (Port: 9100/udp)
3. `network` (Port: 9000/udp)
4. `sensor` 

### Adversarial Testing (Tampering)

To simulate a man-in-the-middle or compromised Fog Node, you can invoke the Cloud's tamper route:

```bash
curl -X POST http://localhost:8000/tamper
```

This will artificially flip computational bits and rigorously evaluate the Cloud's Merkle Proof verification mechanism.

### Analyzing Metrics

You can analyze system metrics visually using the python script provided:

```bash
python analyze_metrics.py
```

This will parse the project's generated `.log` outputs (`fog.log` and `cloud.log`) and output PNG graphs like `latency.png`, `throughput.png`, `verification.png`, and `reconciliation.png`.

## Documentation

For a deep-dive into the specifications, mathematical proofs, and system architecture, consult the following:
- [AWDRN Technical Report](./AWDRN_Technical_Report.md)
- [Features & Functionalities List](./AWDRN_Features_List.md)
