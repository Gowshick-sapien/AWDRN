import socket
import requests
import sqlite3
import struct
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

UDP_PORT = 9100
SIGNATURE_SIZE = 64

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

# Enable WAL mode
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

# Metadata table (for last_counter)
cursor.execute("""
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

conn.commit()

# Load last counter from DB
cursor.execute("SELECT value FROM metadata WHERE key='last_counter'")
row = cursor.fetchone()

if row:
    last_counter = int(row[0])
else:
    last_counter = -1

print(f"Recovered last_counter = {last_counter}")

# ---------------------------
# Main Receive Loop
# ---------------------------

while True:
    data, addr = sock.recvfrom(2048)

    signature = data[-SIGNATURE_SIZE:]
    structured = data[:-SIGNATURE_SIZE]

    # Signature verification
    try:
        verify_key.verify(structured, signature)
    except BadSignatureError:
        print("Signature INVALID - dropped")
        continue

    # Parse structured packet
    counter = struct.unpack(">Q", structured[0:8])[0]
    payload_len = struct.unpack(">H", structured[8:10])[0]
    payload = structured[10:10+payload_len]
    message = payload.decode()

    # Replay protection
    if counter <= last_counter:
        print(f"Replay detected (counter {counter}) - dropped")
        continue

    # Store BEFORE forwarding
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

    # Forward to cloud
    json_payload = {"message": message, "counter": counter}

    try:
        requests.post("http://cloud:8000/ingest", json=json_payload)
    except Exception as e:
        print("Cloud unreachable:", e)