from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/")
def root():
    return {"status": "cloud alive", "time": time.time()}

@app.post("/ingest")
async def ingest(data: dict):
    print("Cloud received:", data)
    return {"status": "ok"}

@app.post("/anchor")
async def anchor(data: dict):
    print("Merkle root anchored:", data)
    return {"status": "stored"}