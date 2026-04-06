import hashlib
import base64
import time
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
tamper_count = 0

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
    global tamper_count
    
    batch_id = data.get("batch_id")
    batch_start = data.get("batch_start")
    batch_end = data.get("batch_end")
    batch_size = data.get("batch_size", 0)
    root = data.get("root")
    proofs = data.get("proofs", [])
    
    t_sent = data.get("timestamp")
    if t_sent:
        t_now = time.time()
        latency = (t_now - t_sent) * 1000
        print(f"[METRIC] End-to-End Latency: {latency:.2f} ms")

    print(f"\nCloud received anchor request for Batch {batch_id} (counters {batch_start}-{batch_end})")

    if batch_size < 8:
        tamper_count += 1
        print(f"[METRIC] Tampering Detected Count: {tamper_count}")
        print("Tampering detected: batch size is smaller than constraint expected!")
        return {"status": "tampered", "reason": "batch_too_small"}
        
    if len(proofs) == 0:
        tamper_count += 1
        print(f"[METRIC] Tampering Detected Count: {tamper_count}")
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
            start_verify = time.time()
            valid = verify_merkle_proof(record_bytes, proof_array, root, leaf_index)
            end_verify = time.time()
            print(f"[METRIC] Verification Time: {(end_verify - start_verify)*1000:.2f} ms")
            
            if not valid:
                tamper_count += 1
                print(f"[METRIC] Tampering Detected Count: {tamper_count}")
                print(f"[ANCHOR VERIFY FAIL] Batch {batch_id}, Index {leaf_index}")
                return {
                    "status": "tampered",
                    "failed_index": leaf_index,
                    "reason": "proof_mismatch"
                }
                
        except Exception as e:
            print(f"Tampering or Decoding Error constraint: {e}")
            return {"status": "tampered", "reason": "payload_corrupt"}

    print(f"Successfully cryptographically verified {len(proofs)} proofs for root: {root}")
    return {"status": "verified"}

@app.post("/reconcile_request")
async def reconcile_request(data: dict):
    batch_id = data.get("batch_id")
    index = data.get("index")
    root = data.get("root")
    record_b64 = data.get("record")
    proof_array = data.get("proof", [])
    
    print(f"\n[RECONCILE RECEIVED] Batch {batch_id}, Index {index}")
    
    try:
        record_bytes = base64.b64decode(record_b64)
        if verify_merkle_proof(record_bytes, proof_array, root, index):
            print("[RECONCILE SUCCESS] Transient error resolved")
            return {"status": "resolved"}
        else:
            print("[RECONCILE FAIL] Proof remains mathematically invalid!")
            return {"status": "persistent_tampering"}
    except Exception as e:
        return {"status": "persistent_tampering", "reason": "decode_error"}