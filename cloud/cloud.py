import hashlib
from fastapi import FastAPI

app = FastAPI()

# ======================================================
# DEVICE REGISTRY (Trust Authority)
# ======================================================

device_registry = {}


@app.post("/register")
async def register(data: dict):

    device_id = data["device_id"]
    public_key = data["public_key"]

    device_registry[device_id] = {
        "public_key": public_key,
        "revoked": False
    }

    print(f"Device registered: {device_id}")

    return {"status": "registered"}


@app.get("/device/{device_id}")
async def get_device(device_id: str):

    device = device_registry.get(device_id)

    if not device:
        return {"error": "unknown device"}

    return device


@app.post("/revoke/{device_id}")
async def revoke(device_id: str):

    if device_id in device_registry:
        device_registry[device_id]["revoked"] = True
        print(f"Device revoked: {device_id}")
        return {"status": "revoked"}

    return {"error": "unknown device"}


# ======================================================
# EXISTING CLOUD SERVICES
# ======================================================

ingested_telemetry = {}

def hash_record(counter, message):
    data = f"{counter}:{message}".encode()
    return hashlib.sha256(data).hexdigest()

def build_merkle_root(hashes):
    if not hashes:
        return ""
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

@app.post("/ingest")
async def ingest(data: dict):
    counter = data.get("counter")
    message = data.get("message")
    if counter is not None:
        ingested_telemetry[counter] = message
    print(f"Cloud received telemetry counter={counter}")
    return {"status": "ok"}


@app.post("/anchor")
async def anchor(data: dict):
    batch_start = data.get("batch_start")
    batch_end = data.get("batch_end")
    provided_root = data.get("merkle_root")

    print(f"Cloud received anchor request for batch {batch_start}-{batch_end}")

    # Reconstruct the batch from ingested data
    relevant_counters = [c for c in ingested_telemetry.keys() if batch_start <= c <= batch_end]

    if not relevant_counters:
        print("Tampering detected: No data found for batch.")
        return {"status": "tampered", "reason": "missing_data"}

    relevant_counters.sort()

    hashes = [hash_record(c, ingested_telemetry[c]) for c in relevant_counters]
    computed_root = build_merkle_root(hashes)

    if computed_root == provided_root:
        print(f"Merkle root verified: {computed_root}")
        return {"status": "verified"}
    else:
        print(f"Tampering detected! Expected root: {provided_root}, Computed root: {computed_root}")
        return {"status": "tampered", "reason": "merkle_root_mismatch"}