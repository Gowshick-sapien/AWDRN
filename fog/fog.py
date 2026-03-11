import socket
import requests
import sqlite3
import struct
import hashlib
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

def hash_record(counter, message):
    data = f"{counter}:{message}".encode()
    return hashlib.sha256(data).hexdigest()

def build_merkle_root(hashes):

    nodes = hashes[:]

    while len(nodes) > 1:

        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])

        new_level = []

        for i in range(0, len(nodes), 2):
            combined = nodes[i] + nodes[i+1]
            new_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_level.append(new_hash)

        nodes = new_level

    return nodes[0]

# ---------------------------
# Batch State
# ---------------------------

batch_buffer = []
batch_start_counter = None

# ---------------------------
# Main Receive Loop
# ---------------------------

while True:

    data, addr = sock.recvfrom(2048)

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
    # Merkle batching
    # ---------------------------

    record_hash = hash_record(counter, message)

    if batch_start_counter is None:
        batch_start_counter = counter

    batch_buffer.append(record_hash)

    if len(batch_buffer) >= BATCH_SIZE:

        root = build_merkle_root(batch_buffer)

        batch_end = counter

        cursor.execute(
            "INSERT INTO merkle_roots (batch_start, batch_end, merkle_root) VALUES (?, ?, ?)",
            (batch_start_counter, batch_end, root)
        )

        conn.commit()

        print(f"Merkle batch committed {batch_start_counter}-{batch_end}")
        print(f"Merkle root: {root}")

        # Send root to cloud
        try:
            requests.post(
                "http://cloud:8000/anchor",
                json={
                    "batch_start": batch_start_counter,
                    "batch_end": batch_end,
                    "merkle_root": root
                }
            )
        except Exception as e:
            print("Merkle anchor failed:", e)

        batch_buffer = []
        batch_start_counter = None

    # ---------------------------
    # Forward to cloud
    # ---------------------------

    json_payload = {"message": message, "counter": counter}

    try:
        requests.post("http://cloud:8000/ingest", json=json_payload)
    except Exception as e:
        print("Cloud unreachable:", e)