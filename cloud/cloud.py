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

@app.post("/ingest")
async def ingest(data: dict):
    print("Cloud received:", data)
    return {"status": "ok"}


@app.post("/anchor")
async def anchor(data: dict):
    print("Merkle root anchored:", data)
    return {"status": "stored"}