import socket
import requests
import sqlite3
import struct
import hashlib
import time
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

UDP_PORT = 9100
SIGNATURE_SIZE = 64
BATCH_SIZE = 8

# Load public key
with open("sensor_public.key", "rb") as f:
    public_key_bytes = f.read()

verify_key = VerifyKey(public_key_bytes)

# Setup UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

print("Fog listening on UDP 9100")

# ---------------------------
# SQLite Initialization
# ---------------------------

DB_FILE = "fog.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("PRAGMA journal_mode=WAL;")

# Telemetry table
cursor.execute("""
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    counter INTEGER UNIQUE,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Metadata table
cursor.execute("""
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

# Merkle roots table
cursor.execute("""
CREATE TABLE IF NOT EXISTS merkle_roots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_start INTEGER,
    batch_end INTEGER,
    merkle_root TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# ---------------------------
# Load last counter
# ---------------------------

cursor.execute("SELECT value FROM metadata WHERE key='last_counter'")
row = cursor.fetchone()

if row:
    last_counter = int(row[0])
else:
    last_counter = -1

print(f"Recovered last_counter = {last_counter}")

# ---------------------------
# Merkle Utilities
# ---------------------------

def build_merkle_tree_with_proofs(leaves):
    if not leaves:
        return "", []
    
    proofs = [[] for _ in leaves]
    nodes = leaves[:]
    node_indices = [[i] for i in range(len(leaves))]
    
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
            node_indices.append(node_indices[-1])
            
        new_level = []
        new_indices = []
        
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i+1]
            
            for leaf_idx in node_indices[i]:
                proofs[leaf_idx].append(right)
            for leaf_idx in node_indices[i+1]:
                proofs[leaf_idx].append(left)
                
            combined = bytes.fromhex(left) + bytes.fromhex(right)
            new_hash = hashlib.sha256(combined).hexdigest()
            
            new_level.append(new_hash)
            new_indices.append(node_indices[i] + node_indices[i+1])
            
        nodes = new_level
        node_indices = new_indices
        
    return nodes[0], proofs

# ---------------------------
# Batch State
# ---------------------------

batch_buffer = []
batch_id = 0

packet_count = 0
start_time = time.time()

# ---------------------------
# Main Receive Loop
# ---------------------------

while True:

    data, addr = sock.recvfrom(2048)
    packet_timestamp = time.time()
    packet_count += 1
    
    if time.time() - start_time >= 5:
        throughput = packet_count / (time.time() - start_time)
        print(f"[METRIC] Throughput: {throughput:.2f} packets/sec")
        packet_count = 0
        start_time = time.time()


    signature = data[-SIGNATURE_SIZE:]
    structured = data[:-SIGNATURE_SIZE]

    # Verify signature
    try:
        verify_key.verify(structured, signature)
    except BadSignatureError:
        print("Signature INVALID - dropped")
        continue

    # Parse packet
    counter = struct.unpack(">Q", structured[0:8])[0]
    payload_len = struct.unpack(">H", structured[8:10])[0]
    payload = structured[10:10+payload_len]

    message = payload.decode()

    # Replay protection
    if counter <= last_counter:
        print(f"Replay detected (counter {counter}) - dropped")
        continue

    # Store telemetry
    try:

        cursor.execute(
            "INSERT INTO telemetry (counter, message) VALUES (?, ?)",
            (counter, message)
        )

        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_counter', ?)",
            (str(counter),)
        )

        conn.commit()

    except sqlite3.IntegrityError:
        print(f"Duplicate counter {counter} - dropped")
        continue

    last_counter = counter

    print(f"VALID packet counter={counter}")
    print("Stored in SQLite")

    # ---------------------------
    # Forward to cloud
    # ---------------------------

    json_payload = {"message": message, "counter": counter}

    try:
        requests.post("http://cloud:8000/ingest", json=json_payload)
    except Exception as e:
        print("Cloud unreachable:", e)

    # ---------------------------
    # Merkle batching and Proof generation
    # ---------------------------

    raw_record_bytes = f"{counter}:{message}".encode()
    batch_buffer.append((counter, raw_record_bytes, packet_timestamp))

    if len(batch_buffer) >= BATCH_SIZE:

        batch_id += 1

        # 1. Deterministic sorting by counter explicitly
        batch_buffer.sort(key=lambda x: x[0])

        batch_start_counter = batch_buffer[0][0]
        batch_end = batch_buffer[-1][0]

        # 2. Extract strictly sha256 hashes of standard raw bytes for the leaves
        leaf_hashes = [hashlib.sha256(item[1]).hexdigest() for item in batch_buffer]
        
        # 3. Build tree and proofs using standard raw byte hex concatenation
        root, proofs = build_merkle_tree_with_proofs(leaf_hashes)

        cursor.execute(
            "INSERT INTO merkle_roots (batch_start, batch_end, merkle_root) VALUES (?, ?, ?)",
            (batch_start_counter, batch_end, root)
        )

        conn.commit()

        print(f"Merkle batch committed {batch_start_counter}-{batch_end}")
        print(f"Merkle root: {root}")

        # 4. Probabilistic sampling exactly as requested
        import random
        import base64
        sample_size = min(2, len(batch_buffer))
        sampled_indices = random.sample(range(len(batch_buffer)), sample_size)
        
        proofs_payload = []
        for idx in sampled_indices:
            raw_bytes = batch_buffer[idx][1]
            b64_record = base64.b64encode(raw_bytes).decode('utf-8')
            proofs_payload.append({
                "record": b64_record,
                "proof": proofs[idx],
                "index": idx
            })

        # Send root and proofs asynchronously to cloud API
        reconcile_attempted = False
        anchor_success = False

        # Use the timestamp of the last packet in the batch for latency calculation
        anchor_timestamp = batch_buffer[-1][2]

        while not anchor_success and not reconcile_attempted:
            try:
                resp = requests.post(
                    "http://cloud:8000/anchor",
                    json={
                        "batch_id": batch_id,
                        "batch_start": batch_start_counter,
                        "batch_end": batch_end,
                        "batch_size": len(batch_buffer),
                        "root": root,
                        "proofs": proofs_payload,
                        "fog_id": "fog_1",
                        "timestamp": anchor_timestamp
                    }
                )
                if resp.status_code == 200:
                    resp_data = resp.json()
                    if resp_data.get("status") == "tampered":
                        failed_idx = resp_data.get("failed_index")
                        print(f"\n[ANCHOR FAILED] Batch {batch_id}, Index {failed_idx}")
                        
                        t_detected = time.time()
                        
                        # Full Reconciliation Protocol
                        reconcile_attempted = True
                        print("[RECONCILE] Sending recovery proof...")
                        
                        raw_bytes = batch_buffer[failed_idx][1]
                        b64_record = base64.b64encode(raw_bytes).decode('utf-8')
                        
                        rec_resp = requests.post(
                            "http://cloud:8000/reconcile_request",
                            json={
                                "batch_id": batch_id,
                                "index": failed_idx,
                                "record": b64_record,
                                "proof": proofs[failed_idx],
                                "root": root
                            }
                        )
                        
                        rec_data = rec_resp.json()
                        if rec_data.get("status") == "resolved":
                            t_resolved = time.time()
                            print("[RECONCILE SUCCESS] Transient error resolved\n")
                            print(f"[METRIC] Reconciliation Time: {t_resolved - t_detected:.4f} sec")
                            anchor_success = True
                        else:
                            print("\n🚨 FATAL: PERSISTENT CLOUD DATA TAMPERING! 🚨\n")
                    else:
                        anchor_success = True
            except Exception as e:
                print("Merkle anchor failed:", e)
                break

        batch_buffer = []