import hashlib
import base64
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
# STATELESS MERKLE VERIFICATION SERVICES
# ======================================================

force_tamper_next_request = False

@app.post("/tamper")
async def tamper():
    global force_tamper_next_request
    force_tamper_next_request = True
    print("User manually triggered tampering for the next incoming anchor request!")
    return {"status": "tampering_armed"}

@app.post("/ingest")
async def ingest(data: dict):
    # The Cloud is now completely stateless and no longer buffers full telemetry for tree reconstruction.
    print(f"Cloud passively received via /ingest: counter={data.get('counter')}")
    return {"status": "ok"}

def verify_merkle_proof(record_bytes: bytes, proof: list, root: str, index: int) -> bool:
    """Verifies a single Merkle Proof probabilistically."""
    computed_hash = hashlib.sha256(record_bytes).hexdigest()
    
    for sibling in proof:
        if index % 2 == 0:
            combined = bytes.fromhex(computed_hash) + bytes.fromhex(sibling)
        else:
            combined = bytes.fromhex(sibling) + bytes.fromhex(computed_hash)
        computed_hash = hashlib.sha256(combined).hexdigest()
        index = index // 2
        
    return computed_hash == root

@app.post("/anchor")
async def anchor(data: dict):
    global force_tamper_next_request
    
    batch_start = data.get("batch_start")
    batch_end = data.get("batch_end")
    batch_size = data.get("batch_size", 0)
    root = data.get("root")
    proofs = data.get("proofs", [])

    print(f"\nCloud received anchor request for batch {batch_start}-{batch_end} (size: {batch_size})")

    if batch_size < 8:
        print("Tampering detected: batch size is smaller than constraint expected!")
        return {"status": "tampered", "reason": "batch_too_small"}
        
    if len(proofs) == 0:
        print("Tampering detected: No proofs appended!")
        return {"status": "tampered", "reason": "no_proofs"}

    # Simulate adversarial tampering dynamically for MVP testing if flagged
    if force_tamper_next_request:
        if len(proofs) > 0:
            # Flip a byte directly inside the first hex string of the first proof
            if len(proofs[0]["proof"]) > 0:
                print("Simulating adversarial proof corruption!")
                original = proofs[0]["proof"][0]
                proofs[0]["proof"][0] = "00" + original[2:]
        force_tamper_next_request = False

    for idx, p in enumerate(proofs):
        try:
            record_b64 = p.get("record")
            proof_array = p.get("proof")
            leaf_index = p.get("index")

            # Must securely decode the canonical bytes exactly as the fog built them
            record_bytes = base64.b64decode(record_b64)

            # Verification short-circuits instantly upon the first cryptographic anomaly
            valid = verify_merkle_proof(record_bytes, proof_array, root, leaf_index)
            if not valid:
                print(f"Tampering detected! Proof {idx+1}/{len(proofs)} computationally failed against root {root}")
                return {"status": "tampered"}
                
        except Exception as e:
            print(f"Tampering or Decoding Error constraint: {e}")
            return {"status": "tampered", "reason": "payload_corrupt"}

    print(f"Successfully cryptographically verified {len(proofs)} proofs for root: {root}")
    return {"status": "verified"}