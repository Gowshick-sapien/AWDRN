# AWDRN: Features & Functionalities List

The AWDRN project is a robust Edge/Fog Computing simulation that focuses heavily on secure data transmission, cryptography, decentralized trust, and scalable verification mechanisms. The architecture spans from a constrained edge device (Sensor) up to a centralized authority (Cloud), with a powerful intermediate gateway (Fog node) handling heavy compute.

Here is a detailed breakdown of the features implemented in the system:

## 1. High-Performance Edge Agent (`sensor_c`)
*   **Low-Level C Implementation:** The sensor is written in bare-metal C for maximum efficiency and speed, suitable for constrained IoT devices.
*   **Ed25519 Cryptography:** Utilizes `libsodium` to generate highly secure cryptographic signatures using Ed25519 private keys.
*   **Custom Binary Protocol:** Bypasses heavy JSON serialization at the edge layer. Data is packed into a strict binary format containing an 8-byte monotonically increasing counter, a 2-byte payload length indicator, the raw telemetry message, and a 64-byte signature block appended dynamically.
*   **UDP Transmission:** Broadcasts data losslessly via UDP packets to maximize throughput.

## 2. Realistic Network Emulation (`network`)
*   **Probabilistic Packet Loss:** Artificially drops roughly 20% of incoming packets to accurately simulate harsh, real-world wireless industrial environments.
*   **Latency Jitter Injection:** Introduces random delays (0 to 500ms) on packets passing through it, forcing the rest of the system to handle data arriving asynchronously or out of order.

## 3. Stateful Edge Validation & Processing (`fog`)
*   **Signature Verification:** The Fog node acts as a zero-trust gateway. Every packet's 64-byte Ed25519 signature is strictly verified against a known public key (`libsodium`/`pynacl`). Unauthorized packets drop instantly.
*   **Replay Attack Protection:** Persists the state of the last valid counter it saw. If a malicious actor intercepts and resends an older, validly signed packet, the Fog node will detect the regression and drop the traffic.
*   **Robust Persistence (SQLite WAL):** Verified traffic is dynamically written into a high-throughput SQLite database running in Write-Ahead Logging (WAL) mode ensuring no data is lost during sudden container stops or edge failures.
*   **Deterministic Merkle Tree Generation:** The fog node groups telemetry into mathematical batches. It explicitly organizes the raw bytes deterministically, generates `hashlib.sha256` byte streams, and assembles a secure Merkle Tree and extracts full mathematical Proofs for the leaves.

## 4. Scalable & Stateless Cloud Verification (`cloud`)
*   **Zero-State Architecture:** The Cloud was heavily upgraded to be completely stateless regarding data parsing. It no longer stores every single piece of telemetry mapping, allowing it to scale massively without localized memory bloat.
*   **Probabilistic Cryptographic Verification:** Rather than checking massive blocks, the Cloud uses fractional verification via Merkle Proofs. It receives 2 randomly sampled records out of an edge batch. It decodes the exact raw bytes and hashes them collaboratively with a provided branching index array to verify the ultimate integrity of the batch.
*   **Short-Circuit Execution:** The verification is perfectly optimized; if even the first parsed proof returns mathematically invalid, it instantly rejects the payload entirely.

## 5. Security Threat Detection & Automated Alerting
*   **Adversarial /tamper System:** The Cloud exposes an explicit API (`/tamper`) to allow administrators to deliberately flip computational bits during flight. This deterministically simulates a sophisticated network assault or a compromised Fog node.
*   **Real-time Fog Alerting:** If the Cloud mathematically deduces tampering during proof evaluation, it signals back to the Fog node over HTTP in real-time. The Fog responds universally, logging critical visual alerts (`🚨 CLOUD DETECTED DATA TAMPERING! 🚨`) upon receiving word its integrity is compromised.
