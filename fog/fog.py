import socket
import requests
import json
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

UDP_PORT = 9100

SIGNATURE_SIZE = 64

with open("sensor_public.key", "rb") as f:
    public_key_bytes = f.read()

verify_key = VerifyKey(public_key_bytes)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

print("Fog listening on UDP 9100")


while True:
    data, addr = sock.recvfrom(2048)

    payload = data[:-SIGNATURE_SIZE]
    signature = data[-SIGNATURE_SIZE:]

    try:
        verify_key.verify(payload, signature)
        print("Signature VALID")
        print("Fog received valid payload:", payload.decode())
    except BadSignatureError:
        print("Signature INVALID - packet dropped")
        continue

    # Use VERIFIED payload only
    json_payload = {"message": payload.decode()}

    try:
        requests.post("http://cloud:8000/ingest", json=json_payload)
    except Exception as e:
        print("Cloud unreachable:", e)